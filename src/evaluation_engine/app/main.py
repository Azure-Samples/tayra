"""
The configuration for the web api.
"""

import json
import logging
import os
import tempfile
from tempfile import NamedTemporaryFile
from urllib.parse import unquote

from azure.storage.blob.aio import BlobServiceClient
from dotenv import find_dotenv, load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.background import run_evaluation_job
from app.jobs import (
    get_blob_properties,
    improve_transcription,
    set_human_evaluation,
    set_unitary_evaluation
)
from app.schemas import (
    RESPONSES,
    BodyMessage,
    HumanEvaluation,
    TranscriptionImprovementRequest,
    TranscriptionJobParams,
    UnitaryEvaluation,
    UploadJobParams,
)

load_dotenv(find_dotenv())

BLOB_CONN = os.getenv("BLOB_CONNECTION_STRING", "")
MODEL_URL: str = os.environ.get("GPT4O_URL", "")
MODEL_KEY: str = os.environ.get("GPT4O_KEY", "")
MONITOR: str = os.environ.get("AZ_CONNECTION_LOG", "")


tags_metadata: list[dict] = [
    {
        "name": "Tarefas em Segundo Plano",
        "description": """
        Endpoints de execução de tarefas em segundo plano para processamento em lotes de arquivos de áudio.
        """,
    },
    {
        "name": "Tarefas Operacionais",
        "description": """
        Tarefas para a visualização e atualização síncrona de registros únicos.
        """,
    }
]

description: str = """
    Uma API Web para gerenciar a análise de transcrições.
"""


app: FastAPI = FastAPI(
    title="Assistente de Análise de Transcrições",
    version="Alpha",
    description=description,
    openapi_tags=tags_metadata,
    openapi_url="/api/v1/openapi.json",
    responses=RESPONSES,  # type: ignore
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError  # pylint: disable=unused-argument
) -> JSONResponse:
    """
    validation_exception_handler Exception handler for validations.

    Args:
        request (Request): the request from the api
        exc (RequestValidationError): the validation raised by the process

    Returns:
        JSONResponse: A json encoded response with the validation errors.
    """

    response_body: BodyMessage = BodyMessage(
        success=False,
        type="Validation Error",
        title="Your request parameters didn't validate.",
        detail={"invalid-params": list(exc.errors())},
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(response_body),
    )


@app.post("/audio-upload", tags=["Tarefas em Segundo Plano"])
async def audio_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    params: str = Form(...),
) -> JSONResponse:
    """
    Uploads an audio file and starts a background task to process it.
    """
    try:
        params_dict = json.loads(params)
        upload_job_params = UploadJobParams(**params_dict)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}") from e

    if file.content_type not in ["application/x-zip-compressed", "audio/mpeg", "audio/wav"]:
        raise HTTPException(
            status_code=400, detail="Tipo de arquivo não suportado. Aceitos: zip, mp3, wav."
        )

    if not file.filename:
        raise AttributeError("Nome de arquivo inválido.")

    _, ext = os.path.splitext(file.filename)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    background_tasks.add_task(run_upload_job, temp_file_path, **upload_job_params.dict())

    return JSONResponse({"result": "Sua requisição está sendo processada."})


@app.post("/transcription", tags=["Tarefas em Segundo Plano"])
async def transcribe(
    background_tasks: BackgroundTasks, params: TranscriptionJobParams
) -> JSONResponse:
    """
    Endpoint para reprocessar lotes de arquivos.
    """
    background_tasks.add_task(run_transcription_job, params)
    return JSONResponse({"result": "Sua requisição está sendo processada."})


@app.post("/evaluate", tags=["Tarefas em Segundo Plano"])
async def evaluate(
    background_tasks: BackgroundTasks, params: TranscriptionJobParams
) -> JSONResponse:
    """
    load_data loads the data into the Context
    """
    background_tasks.add_task(run_evaluation_job, params)
    return JSONResponse({"result": "Sua avaliação está sendo processada."})


@app.get("/overlooker-data", tags=["Tarefas Operacionais"])
async def get_manager_data(manager: str) -> JSONResponse:
    """
    load_data loads the data into the Context
    """
    data = await load_manager_data(manager_name=manager)
    return JSONResponse({"result": data})


@app.get("/transcription-data", tags=["Tarefas Operacionais"])
async def get_transcription_data(specialist: str) -> JSONResponse:
    """
    load_data loads the data into the Context
    """
    decoded_specialist = unquote(specialist)
    data = await load_transcription_data(specialist_name=decoded_specialist)
    print(decoded_specialist)
    return JSONResponse({"result": data})


@app.get("/stream-audio", tags=["Tarefas Operacionais"])
async def download_audio_file(
    request: Request,
    audio_name: str
):
    """
    Download de um arquivo de áudio do Azure Blob Storage.
    """

    blob_path = "/".join(unquote(audio_name).split("/")[1:])
    logging.info("Blob path after decoding: %s", blob_path)

    audio_variants = [
        blob_path.replace(".txt", ".mp3"),
        blob_path.replace(".txt", ".wav"),
        blob_path.replace(".txt", ".ogg")
    ]

    async with BlobServiceClient.from_connection_string(BLOB_CONN) as blob_service:
        for file_path in audio_variants:
            try:
                logging.info("Trying to access file: %s", file_path)
                blob_client = blob_service.get_blob_client(container="audio-files", blob=file_path)
                blob_properties = await get_blob_properties(blob_client)
                if blob_properties:
                    logging.info("Blob size for '%s': %d bytes", file_path, blob_properties.size)

                    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_path)[1]) as tmp_file:
                        download_stream = await blob_client.download_blob()
                        download_data = await download_stream.read()
                        with open(tmp_file.name, "wb") as file:
                            file.write(download_data)

                        logging.info("File downloaded to temporary location: %s", tmp_file.name)
                        break
            except Exception as exc:
                logging.warning("Error downloading audio file '%s': %s", file_path, str(exc))
                continue

    try:
        return FileResponse(
            tmp_file.name,
            media_type="audio/mpeg" if tmp_file.name.endswith(".mp3") else "audio/wav",
            filename=os.path.basename(tmp_file.name),
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(tmp_file.name)}"}
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Audio file not found in any of the attempted formats (.mp3, .wav)."
        ) from exc


@app.post("/human-evaluation", tags=["Tarefas Operacionais"])
async def add_human_evaluation(transcription_id: str, evaluation: HumanEvaluation) -> JSONResponse:
    """
    load_data loads the data into the Context
    """
    data = await set_human_evaluation(transcription_id, evaluation)
    return JSONResponse({"result": data})


@app.post("/unitary-evaluation", tags=["Tarefas Operacionais"])
async def add_unitary_evaluation(evaluation: UnitaryEvaluation) -> JSONResponse:
    """
    load_data loads the data into the Context
    """
    data = await set_unitary_evaluation(evaluation)
    return JSONResponse(data)


@app.post("/transcription-improvement", tags=["Tarefas Operacionais"])
async def set_transcription_improvement(request: TranscriptionImprovementRequest) -> JSONResponse:
    """
    load_data loads the data into the Context
    """
    data = await improve_transcription(request.transcription_data)
    return JSONResponse(data)


@app.post("/chat", tags=["Tarefas Operacionais"])
async def chat_with_data(request: Request) -> JSONResponse:
    """
    Gerencia o chat
    """
    body = await request.json()
    question = body.get("question", "")
    chat_engine = ChatWithCosmos(prompt=question)
    response = await chat_engine()
    return JSONResponse(response, media_type="text/plain")
