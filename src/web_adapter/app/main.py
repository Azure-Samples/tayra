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

from app import __version__, __app__
from app.background import run_upload_job
from app.ingest import get_blob_properties
from app.schemas import RESPONSES, BodyMessage, UploadJobParams


load_dotenv(find_dotenv())

BLOB_CONN = os.getenv("BLOB_CONNECTION_STRING", "")
MODEL_URL: str = os.environ.get("GPT4O_URL", "")
MODEL_KEY: str = os.environ.get("GPT4O_KEY", "")
MONITOR: str = os.environ.get("AZ_CONNECTION_LOG", "")


tags_metadata: list[dict] = [
    {
        "name": "Background Tasks",
        "description": """
        Endpoints for executing background tasks for operating asynchronous tasks.
        """,
    },
    {
        "name": "Operational Tasks",
        "description": """
        Endpoints associated with synchronous responses for navigating users.
        """,
    },
]

description: str = """
    Web API to manage audio ingestion from a Call Center.\n
    Leveraging Azure Blob Storage, this engine enables easy integration with diferent call center audio sources.
    Those audios are transcribed and then used on subsequent evaluations.
"""


app: FastAPI = FastAPI(
    title=__app__,
    version=__version__,
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


@app.post("/audio-upload", tags=["Background Tasks"])
async def audio_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    params: str = Form(...),
) -> JSONResponse:
    """
    ## Handles the upload of audio files and initiates a background task to process the upload.\n\n
    **Args**:\n
        background_tasks (BackgroundTasks): FastAPI's background tasks manager to handle background operations.\n
        file (UploadFile): The uploaded file object.\n
        params (str): JSON string containing additional parameters for the upload job.\n
    **Returns**:\n\n
        JSONResponse: A JSON response indicating that the request is being processed.\n
    **Raises**:\n\n
        HTTPException: If the provided JSON in `params` is invalid or if the file type is not supported.\n
        AttributeError: If the uploaded file does not have a valid filename.\n
    """
    try:
        params_dict = json.loads(params)
        upload_job_params = UploadJobParams(**params_dict)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}") from e

    if file.content_type not in ["application/x-zip-compressed", "audio/mpeg", "audio/wav"]:
        raise HTTPException(
            status_code=400, detail="Unsuported file type. Accepted: zip, mp3, wav."
        )

    if not file.filename:
        raise AttributeError("Invalid File Name.")

    _, ext = os.path.splitext(file.filename)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(await file.read())
        temp_file_path = temp_file.name

    background_tasks.add_task(run_upload_job, temp_file_path, **upload_job_params.model_dump())

    return JSONResponse({"result": "Your request is being processed."})


@app.get("/audio-download", tags=["Operational Tasks"])
async def download_audio_file(
    request: Request,
    audio_name: str
):
    """
    ## Downloads an audio file from a blob storage service in one of the supported formats (.mp3, .wav).\n\n
    **Args**:\n
        request (Request): The HTTP request object.\n
        audio_name (str): The name of the audio file to be downloaded, URL-encoded.\n\n
    **Returns**:\n
        FileResponse: A response containing the downloaded audio file.\n\n
    **Raises**:\n
        HTTPException: If the audio file is not found in any of the attempted formats.
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
