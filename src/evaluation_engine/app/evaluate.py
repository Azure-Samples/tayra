import datetime
import logging
import os
import sys
import time
from uuid import uuid4

from azure.cosmos.aio import CosmosClient
from dotenv import find_dotenv, load_dotenv
from promptflow.core import Prompty, AzureOpenAIModelConfiguration
from promptflow.tracing import trace

from app.schemas import (
    HumanEvaluation,
    EvaluationJob,
    Transcription
)


load_dotenv(find_dotenv())

BLOB_CONN = os.getenv("BLOB_CONNECTION_STRING", "")
SAS_TOKEN = os.getenv("BLOB_SERVICE_CLIENT", "")
AI_STUDIO_KEY = os.getenv("AI_STUDIO_KEY", "")
GPT4O_KEY = os.getenv("GPT4O_KEY", "")
GPT4O_URL = os.getenv("GPT4O_URL", "")
COSMOS_ENDPOINT = os.getenv("NEW_COSMOS_ENDPOINT", "")
COSMOS_KEY = os.getenv("NEW_COSMOS_KEY", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class EvaluateTranscription:

    def __init__(
            self,
            model_config: AzureOpenAIModelConfiguration,
            job_config: EvaluationJob
        ):
        self.client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        self.model_config = model_config
        self.job_config = job_config

    async def __call__(self, transcription: dict):
        logger.info("Starting the process to evaluate transcriptions...")
        start_time = time.time()
        async with self.client as cosmos_client:
            database = cosmos_client.get_database_client(DATABASE_NAME)
            output_container = database.get_container_client(self.job_config.cosmosoutput)
            evaluation = await self.process_document(Transcription(
                transcription = transcription.get("transcription", ""),
                theme = self.job_config.theme,
                criteria = self.job_config.criteria
            ))
            evaluation["transcription_id"] = transcription.get("id", "")
            await output_container.upsert_item(evaluation)
            logger.info("Document %s processed.", evaluation.get("id"))
        logger.info("The evaluation process has taken: %s seconds", time.time() - start_time)
        return evaluation

    async def process_document(self, transcription: Transcription):

        evaluation = await self.evaluate(transcription)

        metadata = {
            "date": str(datetime.datetime.today()),
            "duration": evaluation.get("duration", "N/A")
        }

        output_doc = {
            "id": str(uuid4()),
            "transcription": transcription.get("transcription", ""),
            "evaluation": evaluation,
            "metadata": metadata
        }
        return output_doc

    @trace
    async def evaluate(self, transcription: dict):
        start = time.time()
        prompty = Prompty.load(
            source=f"{BASE_DIR}/prompts/evaluate.prompty",
            model={"configuration": self.model_config},
        )
        output = prompty(
            transcription=transcription.get("transcription", ""),
            theme=transcription.get("theme", ""),
            criteria=transcription.get("criteria", {})
        )
        logger.info("Evaluation took: %s seconds", time.time() - start)
        return output


async def set_human_evaluation(transcription_id: str, evaluation: HumanEvaluation):
    evaluation_data = evaluation.model_dump()
    evaluation_data["evaluation_date"] = datetime.datetime.today()
    async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as cosmos_client:
        database = cosmos_client.get_database_client(DATABASE_NAME)
        container = database.get_container_client(os.getenv("HUMAN_EVAL_CONTAINER", ""))
        query = f"SELECT * FROM c WHERE c.transcription_id = {transcription_id}"
        parameters = [{"name": "@transcription_id", "value": transcription_id}]
        items = container.query_items(
            query=query,
            parameters=parameters  # type: ignore
        )
        try:
            async for item in items:
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
        self.client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
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
        evaluation = await self.evaluate(transcription.get("transcription", ""))
        metadata = {
            "date": str(datetime.datetime.today()),
            "duration": evaluation.get("duration", "N/A")
        }
        output_doc = {
            "id": transcription.get("id", ""),
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
