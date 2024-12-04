"""
This FastAPI application provides endpoints for managing people and rules data.
It includes functionality for uploading and querying manager and rule data, with integration to Azure Cosmos DB for data storage.
The API also handles validation errors and supports CORS.
"""

import os

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions

from app import __app__, __version__
from app.schemas import RESPONSES, BodyMessage, ManagerInterface, Criteria


load_dotenv(find_dotenv())

COSMOS_ENDPOINT: str = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_KEY: str = os.getenv("COSMOS_KEY", "")
COSMOS_DB_MANAGER_RULES: str = os.getenv("COSMOS_DB_MANAGER_RULES", "")
DEFAULT_CREDENTIALS = DefaultAzureCredential()


tags_metadata: list[dict] = [
    {
        "name": "People Management",
        "description": """
        Endpoints to manage people data.
        """,
    },
    {
        "name": "Rules Management",
        "description": """
        Endpoints to manage rules data.
        """,
    }
]

description: str = """
    A Web API for basic data management on people and rules.
    This is the major interface with Tayra Application.
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


@app.post("/create-manager", tags=["People Management"])
async def upsert_manager(manager_data: ManagerInterface) -> JSONResponse:
    """
    Uploads an audio file and starts a background task to process it.
    """
    async with CosmosClient(COSMOS_ENDPOINT, credential=DEFAULT_CREDENTIALS) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(COSMOS_DB_MANAGER_RULES)
            await database.read()
        except exceptions.CosmosResourceNotFoundError:
            await cosmos_client.create_database(COSMOS_DB_MANAGER_RULES)

        container = database.get_container_client("managers")
        await container.read()

        manager_data_dict = manager_data.model_dump()
        await container.create_item(body=manager_data_dict, priority="High")

    response_body = BodyMessage(
        success=True,
        type="Upload Success",
        title="Manager data uploaded successfully.",
        detail={"manager": manager_data_dict.get("id")},
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(response_body),
    )


@app.post("/create-rule", tags=["Rules Management"])
async def upsert_rule(rule_data: Criteria) -> JSONResponse:
    """
    Uploads an audio file and starts a background task to process it.
    """
    async with CosmosClient(COSMOS_ENDPOINT, credential=DEFAULT_CREDENTIALS) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(COSMOS_DB_MANAGER_RULES)
            await database.read()
        except exceptions.CosmosResourceNotFoundError:
            await cosmos_client.create_database(COSMOS_DB_MANAGER_RULES)

        container = database.get_container_client("rules")
        await container.read()

        rule_data_dict = rule_data.model_dump()
        print(rule_data_dict, "\n")
        await container.create_item(body=rule_data_dict, priority="High")

    response_body = BodyMessage(
        success=True,
        type="Upload Success",
        title="Rule data uploaded successfully.",
        detail={"rule": rule_data_dict.get("id")},
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(response_body),
    )


@app.get("/managers-names", tags=["People Management"])
async def managers_names() -> JSONResponse:
    """
    Uploads an audio file and starts a background task to process it.
    """
    async with CosmosClient(COSMOS_ENDPOINT, credential=DEFAULT_CREDENTIALS) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(COSMOS_DB_MANAGER_RULES)
            await database.read()
        except exceptions.CosmosResourceNotFoundError:
            await cosmos_client.create_database(COSMOS_DB_MANAGER_RULES)
        container = database.get_container_client("managers")

        query = "SELECT c.name, c.specialists FROM c"
        managers = [
            {
                "name": item['name'],
                "specialists": [
                    specialist["name"] for specialist in item["specialists"]
                ]
            }
            async for item
            in container.query_items(query)
        ]

    response_body = BodyMessage(
        success=True,
        type="Query Success",
        title="Managers names retrieved successfully.",
        detail={"managers": managers},
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_body),
    )


@app.get("/rules", tags=["Rules Management"])
async def list_rules() -> JSONResponse:
    """
    Uploads an audio file and starts a background task to process it.
    """
    async with CosmosClient(COSMOS_ENDPOINT, credential=DEFAULT_CREDENTIALS) as cosmos_client:
        try:
            database = cosmos_client.get_database_client(COSMOS_DB_MANAGER_RULES)
            await database.read()
        except exceptions.CosmosResourceNotFoundError:
            await cosmos_client.create_database(COSMOS_DB_MANAGER_RULES)
        container = database.get_container_client("rules")

        query = "SELECT * FROM c"
        rules = [item async for item in container.query_items(query)]

    response_body = BodyMessage(
        success=True,
        type="Query Success",
        title="Rules retrieved successfully.",
        detail={"rules": rules},
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder(response_body),
    )
