"""
The configuration for the web api.
"""

import os

from promptflow import _PFClient
from promptflow.core import AzureOpenAIModelConfiguration

from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions

from dotenv import find_dotenv, load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __app__, __version__

from app.background import run_evaluation_job
from app.evaluate import TranscriptionImprover, set_human_evaluation
from app.schemas import (
    RESPONSES,
    BodyMessage,
    HumanEvaluation,
    TranscriptionImprovementRequest,
    EvaluationEndpoint
)


load_dotenv(find_dotenv())

BLOB_CONN = os.getenv("BLOB_CONNECTION_STRING", "")
MODEL_URL: str = os.environ.get("GPT4_URL", "")
MODEL_KEY: str = os.environ.get("GPT4_KEY", "")
MONITOR: str = os.environ.get("AZ_CONNECTION_LOG", "")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")

MODEL_CONFIG = AzureOpenAIModelConfiguration(
    azure_deployment="tayra-gpt-4o",
    azure_endpoint=MODEL_URL,
    api_version="2024-08-01-preview",
    api_key=MODEL_KEY
)


tags_metadata: list[dict] = [
    {
        "name": "Background Tasks",
        "description": """
        Endpoints for executing background tasks for operating asynchronous tasks.
        """,
    },
    {
        "name": "Improvement Tasks",
        "description": """
        Tasks associated with evaluation and transcription enhancement.
        """,
    }
]

description: str = """
    Web API to manage transcription evaluation jobs from a Call Center.\n
    Leveraging Azure OpenAI, this engine provides interfaces and engines for evaluating transcriptions agains
    aghnostic criterias. It also provides interfaces for improving existing transcriptions.
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


@app.post("/evaluate", tags=["Background Tasks"])
async def evaluate(background_tasks: BackgroundTasks, params: EvaluationEndpoint) -> JSONResponse:
    """
    ## Asynchronously evaluates the given parameters by starting a background task.\n

    This function initiates a background task to run an evaluation job with the provided parameters
    and model configuration. It immediately returns a JSON response indicating that the background
    process has started.\n\n

    **Args**:\n
        background_tasks (BackgroundTasks): FastAPI's BackgroundTasks instance to manage background tasks.\n
        params (EvaluationEndpoint): The parameters required for the evaluation job.\n\n

    **Returns**:\n
        JSONResponse: A JSON response indicating that the background process has started.
    """
    background_tasks.add_task(run_evaluation_job, params)
    return JSONResponse({"result": "Background process started."})


@app.post("/human-evaluation", tags=["Improvement Tasks"])
async def add_human_evaluation(transcription_id: str, evaluation: HumanEvaluation) -> JSONResponse:
    """
    ## Add a human evaluation to a transcription.\n\n
    **Args**:\n
        transcription_id (str): The ID of the transcription to be evaluated.\n
        evaluation (HumanEvaluation): The human evaluation data to be added.\n\n
    **Returns**:\n
        JSONResponse: A JSON response containing the result of the evaluation addition.
    """
    data = await set_human_evaluation(transcription_id, evaluation)
    return JSONResponse({"result": data})


@app.post("/transcription-improvement", tags=["Improvement Tasks"])
async def improve_transcription(request: TranscriptionImprovementRequest) -> JSONResponse:
    """
    ## Improve the transcription data provided in the request.\n\n
    **Args**:\n
        request (TranscriptionImprovementRequest): The request object containing transcription data to be improved.\n\n
    **Returns**:\n
        JSONResponse: The response object containing the improved transcription data.
    """
    improvement_flow = TranscriptionImprover(model_config=MODEL_CONFIG)
    response = _PFClient().run(flow=improvement_flow, data=request.transcription_data)
    return JSONResponse(response)


@app.get("/specialist-evaluation", tags=["Improvement Tasks"])
async def get_specialist_evaluations(transcription_id: str) -> JSONResponse:
    """
    ## Improve the transcription data provided in the request.\n\n
    **Args**:\n
        request (TranscriptionImprovementRequest): The request object containing transcription data to be improved.\n\n
    **Returns**:\n
        JSONResponse: The response object containing the improved transcription data.
    """
    async with CosmosClient(COSMOS_ENDPOINT, DefaultAzureCredential()) as client:
        try:
            database = client.get_database_client(os.getenv("COSMOS_DB_EVALUATION", "evaluation_job"))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            client.create_database(os.getenv("COSMOS_DB_EVALUATION", "evaluation_job"))
        container = database.get_container_client(os.getenv("CONTAINER_NAME", "evaluations"))
        query = "SELECT * FROM c"
        evaluations = [
            {
                "transcription_id": item["transcription_id"],
                "classification": item["evaluation"]["evaluation"]["classification"],
                "summaryData": item["evaluation"]["evaluation"]["criteria"],
                "improvementSugestion": item["evaluation"]["evaluation"]["improvement_suggestion"]
            }
            async for item in container.query_items(query=query)
            if item["transcription_id"] == transcription_id
        ]

    return JSONResponse({"result": evaluations})
