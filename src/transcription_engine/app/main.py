"""
The configuration for the transcription engine communication.
"""

import os
from urllib.parse import unquote

from dotenv import find_dotenv, load_dotenv

from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__, __app__
from app.background import run_transcription_job
from app.schemas import RESPONSES, BodyMessage, TranscriptionJobParams
from app.database import TranscriptionDatabase


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
    Web API to manage transcription jobs from a Call Center.\n
    Leveraging Azure Cognitive Services, this engine transcribes the audio files into text, which are then stored in Transcription Storage (Azure Cosmos DB).
    Transcriptions are the foundation for all subsequent evaluations in the evaluation engine.
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

database = TranscriptionDatabase()


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



@app.post("/transcription", tags=["Background Tasks"])
async def transcribe(
    background_tasks: BackgroundTasks, params: TranscriptionJobParams
) -> JSONResponse:
    """
    ## Asynchronously handles a transcription request by adding a transcription job to the background tasks.\n\n
    **Args**:\n
        background_tasks (BackgroundTasks): The background tasks manager to which the transcription job will be added.\n
        params (TranscriptionJobParams): The parameters required to run the transcription job.\n\n
    **Returns**:\n
        JSONResponse: A JSON response indicating that the transcription request is being processed.
    """
    background_tasks.add_task(run_transcription_job, params)
    return JSONResponse({"result": "Sua requisição está sendo processada."})


@app.get("/manager-data", tags=["Operational Tasks"])
async def get_manager_data() -> JSONResponse:
    """
    ## Fetches manager data asynchronously from the database.\n
    This function retrieves the names of managers from the database and returns them
    in a JSON response.\n\n
    **Returns**:\n
        JSONResponse: A response object containing the manager names in JSON format.
    """
    data = await database.load_managers_names()
    return JSONResponse({"result": data})


@app.get("/transcription-data", tags=["Operational Tasks"])
async def get_transcription_data(manager: str) -> JSONResponse:
    """
    ## Asynchronously retrieves transcription data for a given specialist.\n\n
    **Args**:\n
        specialist (str): The name of the specialist, URL-encoded.\n\n
    **Returns**:\n
        JSONResponse: A JSON response containing the transcription data.\n\n
    **Raises**:\n
        Exception: If there is an error in loading the data from the database.
    """
    decoded_manager = unquote(manager)
    data = await database.load_manager_data(manager_name=decoded_manager)
    return JSONResponse({"result": data})


@app.get("/specialist-data", tags=["Operational Tasks"])
async def get_specialist_data(specialist: str) -> JSONResponse:
    """
    ## Asynchronously retrieves transcription data for a given specialist.\n\n
    **Args**:\n
        specialist (str): The name of the specialist, URL-encoded.\n\n
    **Returns**:\n
        JSONResponse: A JSON response containing the transcription data.\n\n
    **Raises**:\n
        Exception: If there is an error in loading the data from the database.
    """
    decoded_id = unquote(specialist)
    data = await database.load_transcription_data(specialist_id=decoded_id)
    return JSONResponse({"result": data})


@app.get("/transcriptions", tags=["Operational Tasks"])
async def get_transcriptions() -> JSONResponse:
    """
    ## Asynchronously retrieves transcription data for a given specialist.\n\n
    **Args**:\n
        specialist (str): The name of the specialist, URL-encoded.\n\n
    **Returns**:\n
        JSONResponse: A JSON response containing the transcription data.\n\n
    **Raises**:\n
        Exception: If there is an error in loading the data from the database.
    """
    data = await database.load_transcriptions()
    return JSONResponse({"result": data})
