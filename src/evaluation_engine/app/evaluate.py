import asyncio
import datetime
import json
import logging
import os
import sys
import time
from string import Template
from typing import Optional

import httpx
from azure.cosmos.aio import CosmosClient
from dotenv import find_dotenv, load_dotenv
from promptflow.core import Prompty, AzureOpenAIModelConfiguration
from promptflow.tracing import trace
from promptflow.evals.evaluate import evaluate

from app.prompts import (
    AUGUMENTED_TRANSCRIPTION_PROMPT,
    DEFAULT_SYSTEM_MESSAGE,
    EVALUATION_PROMPT,
    EVALUATION_TYPES,
    SINGLE_EVALUATION_PROMPT,
    SUMMARIZATION_PROMPT,
)
from app.schemas import (
    AditionalEvaluation,
    HumanEvaluation,
    Item,
    SingleEvaluationTemplate,
    UnitaryEvaluation,
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

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class EvaluateTranscription:

    def __init__(
            self,
            model_config: AzureOpenAIModelConfiguration
        ):
        self.model_config = model_config
        self.client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

    async def __call__(self, cosmosinput: str, cosmosoutput: str, limit: int = 1):
        logger.info("Starting the process to evaluate transcriptions...")
        start_time = time.time()
        async with self.client as cosmos_client:
            database = cosmos_client.get_database_client(DATABASE_NAME)
            input_container = database.get_container_client(cosmosinput)
            output_container = database.get_container_client(cosmosoutput)
            query = "SELECT * FROM c"
            counter = 0
            async for item in input_container.query_items(query=query):
                evaluation = await self.process_document(item)
                await output_container.upsert_item(evaluation)
                logger.info("Document %s processed.", item.get("id"))
                counter += 1
                if counter == limit:
                    break

        end_time = time.time()
        duration = end_time - start_time
        logger.info("The evaluation process has taken: %s seconds", duration)

    async def process_document(self, doc: dict):

        response = await self.evaluate(
            os.environ.get("TRANSCRIPTION_QUESTION", ""), doc.get("transcription", "")
        )

        metadata = doc.get("metadata", {})
        metadata["evaluation_date"] = str(datetime.datetime.today())
        metadata["evaluation_duration"] = response.get("duration", "N/A")

        output_doc = {
            "id": doc.get("id"),
            "manager": doc.get("manager_name"),
            "assistant": doc.get("assistant_name"),
            "filename": doc.get("filename"),
            "transcription": doc.get("transcription"),
            "evaluation": response.get("transcription_output"),
            "is_valid_call": response.get("is_valid_call"),
            "metadata": metadata
        }
        return output_doc

    async def evaluate(self, question: str, transcription: str):
        start = time.time()
        data = {"question": question, "transcription": transcription}
        url = "https://transcription-evaluation.swedencentral.inference.ml.azure.com/score"

        headers = {
            "Content-Type": "application/json",
            "Authorization": ("Bearer " + AI_STUDIO_KEY),
            "azureml-model-deployment": "transcription-evaluation-01",
        }

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                duration = time.time() - start
                result = {}
                result["transcription_output"] = json.loads(response.json().get("transcription_output", {}))
                result["is_valid_call"] = response.json().get("is_valid_call", "NÃO")
                result["duration"] = duration
            except httpx.NetworkError as exc:
                logger.error("Network Error: %s. Trying Again.", str(exc))
                await asyncio.sleep(0.5)
                return await self.evaluate_transcription(question, transcription)
            except httpx.HTTPStatusError as exc:
                if response.status_code in [503, 429, 500]:
                    logger.error(
                        "Server error %s: %s. Trying Again.", response.status_code, str(exc)
                    )
                    await asyncio.sleep(60 if response.status_code == 429 else 120)
                    return await self.evaluate_transcription(question, transcription)
                logger.critical("Unhandled HTTP error: %s.", str(exc))
                print("Exception: ", exc.__dict__, "\n", exc.response.__dict__)
                raise exc
            except Exception as exc:
                logger.critical("Unhandled error: %s.", str(exc))
                raise exc
            else:
                return result


class EnhanceEvaluator:

    def __init__(self):
        self.cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

    async def retrieve_history(self):
        return ""

    async def retrieve_context(self):
        return ""

    async def prepare_request(self, prompt_template: PromptTemplate):
        return Template(self.prompt_template).safe_substitute(**prompt_template.model_dump())

    async def save_to_database(self, transcription_id: str, evaluation: AditionalEvaluation):
        evaluation_data = evaluation.model_dump()
        evaluation_data["evaluation_date"] = datetime.datetime.today()
        async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as cosmos_client:
            database = cosmos_client.get_database_client(DATABASE_NAME)
            container = database.get_container_client("evaluation")
            query = "SELECT * FROM c WHERE c.id = @transcription_id"
            parameters = [{"name": "@id", "value": transcription_id}]
            items = container.query_items(
                query=query,
                parameters=parameters,  # type: ignore
                enable_cross_partition_query=True,
            )
            try:
                async for item in items:
                    item["aditional_evaluation"] = evaluation_data
                    container.upsert_item(item)
            except Exception as exc:
                logger.error("Error setting aditional evaluation: %s", str(exc))


async def evaluate_transcription(transcription_id: str, evaluation_type: Optional[str] = None):
    evaluator = EnhanceEvaluator(aistudio_url = GPT4O_URL, aistudio_key = GPT4O_KEY)
    evaluator.system_message = DEFAULT_SYSTEM_MESSAGE
    if not evaluation_type:
        evaluation_type = '\n'.join(EVALUATION_TYPES)
    request_param = {
        "temperature": 0.0,
        "top_p": 0.95,
        "max_tokens": 2000,
    }
    async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as cosmos_client:
        database = cosmos_client.get_database_client(DATABASE_NAME)
        container = database.get_container_client("transcribed_files")
        query = "SELECT c.transcription FROM c WHERE c.id = @transcription_id"
        parameters = [{"name": "@transcription_id", "value": transcription_id}]
        items = container.query_items(
            query=query,
            parameters=parameters  # type: ignore
        )
        async for item in items:
            prompt = EVALUATION_PROMPT.format(criterios=evaluation_type, transcricao=item)
            prompt = PromptTemplate(prompt=prompt)
            response = await evaluator(template=prompt, parameters=request_param)  #type: ignore
            print(response)


async def set_human_evaluation(transcription_id: str, evaluation: HumanEvaluation):
    evaluation_data = evaluation.model_dump()
    evaluation_data["evaluation_date"] = datetime.datetime.today()
    async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as cosmos_client:
        database = cosmos_client.get_database_client(DATABASE_NAME)
        container = database.get_container_client("evaluation")
        query = "SELECT * FROM c WHERE c.id = @transcription_id"
        parameters = [{"name": "@id", "value": transcription_id}]
        items = container.query_items(
            query=query,
            parameters=parameters,  # type: ignore
            enable_cross_partition_query=True
        )
        try:
            async for item in items:
                item["human_evaluation"] = evaluation_data
                container.upsert_item(item)
                return item
        except Exception as exc:
            logger.error("Error setting human evaluation: %s", str(exc))


class SingleEvaluator(FunctionCallingGenerator):

    async def retrieve_history(self):
        return ""

    async def retrieve_context(self):
        return ""

    async def prepare_request(self, prompt_template: PromptTemplate):
        return Template("Você deve trabalhar com a segunte descrição de $tipo: $transcription. $prompt").safe_substitute(**prompt_template.model_dump())


async def set_unitary_evaluation(evaluation: UnitaryEvaluation):
    evaluator = SingleEvaluator(aistudio_url=GPT4O_URL, aistudio_key=GPT4O_KEY)
    evaluator.system_message = SINGLE_EVALUATION_PROMPT
    prompt_template = SingleEvaluationTemplate(prompt=evaluation.prompt, tipo=evaluation.tipo, transcription=evaluation.transcription)
    functions = [
        AzureAIFunction(
            name="EvaluationSchema",
            description="Formata a resposta em JSON. Inclui SubItems para respostas com mais de uma pergunta.",
            parameters=Item.model_json_schema()
        ),
    ]
    evaluator.functions = functions
    req_parameters = {
        "temperature": 0.0,
        "top_p": 0.8,
        "max_tokens": 2000,
        "seed": 42
    }
    response = await evaluator(prompt_template, parameters=req_parameters)  #type: ignore
    response["item"] = evaluation.tipo
    return response


class TranscriptionImprover(PromptGenerator):

    async def retrieve_history(self):
        return ""

    async def retrieve_context(self):
        return ""

    async def prepare_request(self, prompt_template: PromptTemplate):
        return Template(AUGUMENTED_TRANSCRIPTION_PROMPT).safe_substitute(**prompt_template.model_dump())


async def improve_transcription(transcription_data: str):
    evaluator = TranscriptionImprover(aistudio_url=GPT4O_URL, aistudio_key=GPT4O_KEY)
    evaluator.system_message = SUMMARIZATION_PROMPT
    prompt_template = PromptTemplate(prompt=transcription_data)
    req_parameters = {
        "temperature": 0.0,
        "top_p": 0.8,
        "max_tokens": 2000,
        "seed": 42
    }
    response = await evaluator(prompt_template, parameters=req_parameters)  #type: ignore
    return response
