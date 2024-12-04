import datetime
import logging
import os
import sys
import time
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from azure.cosmos import exceptions
from dotenv import find_dotenv, load_dotenv
from promptflow.core import Prompty, AzureOpenAIModelConfiguration
from promptflow.tracing import trace

from app.schemas import HumanEvaluation, Transcription


load_dotenv(find_dotenv())

DEFAULT_CREDENTIAL = DefaultAzureCredential()
MODEL_URL: str = os.environ.get("GPT4_URL", "")
MODEL_KEY: str = os.environ.get("GPT4_KEY", "")
MODEL_NAME: str = os.environ.get("GPT4_NAME", "")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_CONFIG = AzureOpenAIModelConfiguration(
    azure_deployment=MODEL_NAME,
    azure_endpoint=MODEL_URL,
    api_version="2024-08-01-preview",
    api_key=MODEL_KEY
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class EvaluateTranscription:

    def __init__(
            self,
            model_config: AzureOpenAIModelConfiguration = MODEL_CONFIG
        ):
        self.model_config = model_config

    def __call__(self, transcription: Transcription):
        logger.info("Starting the process to evaluate transcriptions...")
        start_time = time.time()
        with CosmosClient(COSMOS_ENDPOINT, DEFAULT_CREDENTIAL) as client:
            try:
                database = client.get_database_client(
                    os.getenv("COSMOS_DB_EVALUATION", "evaluation_job")
                )
                database.read()
            except exceptions.CosmosResourceNotFoundError:
                client.create_database(
                    os.getenv("COSMOS_DB_EVALUATION", "evaluation_job")
                )
            container = database.get_container_client(
                os.getenv("CONTAINER_NAME", "evaluations")
            )
            evaluation = self.process_document(transcription)
            evaluation["transcription_id"] = transcription["id"]
            container.upsert_item(evaluation)
            logger.info("Document %s processed.", evaluation.get("id"))
        logger.info("The evaluation process has taken: %s seconds", time.time() - start_time)
        return evaluation

    def process_document(self, transcription: Transcription):
        evaluation = self.evaluate(transcription)

        metadata = {
            "date": str(datetime.datetime.today()),
            "duration": evaluation.get("duration", "N/A")
        }

        output_doc = {
            "id": str(uuid4()),
            "transcription": transcription["transcription"],
            "evaluation": evaluation,
            "metadata": metadata
        }

        return output_doc

    @trace
    def evaluate(self, transcription: dict):
        start = time.time()
        prompty = Prompty.load(
            source=f"{BASE_DIR}/prompts/evaluate.prompty",
            model={"configuration": self.model_config},
        )
        output = prompty(
            transcription=transcription["transcription"],
            theme=transcription["theme"],
            criteria=transcription["criteria"]
        )
        logger.info("Evaluation took: %s seconds", time.time() - start)
        return output


def set_human_evaluation(transcription_id: str, evaluation: HumanEvaluation):
    evaluation_data = evaluation.model_dump()
    evaluation_data["evaluation_date"] = datetime.datetime.today()
    with CosmosClient(COSMOS_ENDPOINT, DEFAULT_CREDENTIAL) as client:
        try:
            database = client.get_database_client(os.getenv("COSMOS_DB_EVALUATION", "evaluation_job"))
            database.read()
        except exceptions.CosmosResourceNotFoundError:
            client.create_database(os.getenv("COSMOS_DB_EVALUATION", "evaluation_job"))
        container = database.get_container_client(os.getenv("HUMAN_CONTAINER_NAME", "humanEvaluations"))
        query = f"SELECT * FROM c WHERE c.transcription_id = {transcription_id}"
        parameters = [{"name": "@transcription_id", "value": transcription_id}]
        items = container.query_items(
            query=query,
            parameters=parameters  # type: ignore
        )
        try:
            for item in items:
                item["human_evaluation"] = evaluation_data
                container.upsert_item(item)
                return item
        except Exception as exc:
            logger.error("Error setting human evaluation: %s", str(exc))


class TranscriptionImprover:

    def __init__(
            self,
            model_config: AzureOpenAIModelConfiguration
        ):
        self.model_config = model_config

    async def __call__(self, transcription: str):
        logger.info("Starting the process to evaluate transcriptions...")
        start_time = time.time()
        evaluation = await self.process_document({
            "transcription": transcription
        })
        logger.info("The evaluation process has taken: %s seconds", time.time() - start_time)
        return evaluation

    async def process_document(self, transcription: dict):
        evaluation = await self.evaluate(transcription["transcription"])
        metadata = {
            "date": str(datetime.datetime.today()),
            "duration": evaluation.get("duration", "N/A")
        }
        output_doc = {
            "id": transcription["id"],
            "transcription": evaluation,
            "metadata": metadata
        }
        return output_doc

    @trace
    async def evaluate(self, transcription: str):
        start = time.time()
        prompty = Prompty.load(
            source=f"{BASE_DIR}/prompts/enhance.prompty",
            model={"configuration": self.model_config},
        )
        output = prompty(transcription=transcription)
        logger.info("Evaluation took: %s seconds", time.time() - start)
        return output
