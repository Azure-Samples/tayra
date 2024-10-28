"""
This module contains functions for loading data from the Cosmos DB.
Functions:
    load_manager_data(manager_name: Any) -> Dict: Loads manager data
        from the evaluation container in the Cosmos DB based on the given manager name.
    load_transcription_data(specialist_name: Any) -> List[Dict]: Loads transcription data
        for a given specialist name.
"""

import logging
import os
import sys
from typing import Dict, List

from azure.core import exceptions as azure_exceptions
from azure.identity import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient


COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.getenv("COSMOS_KEY", "")
DATABASE_NAME = os.getenv("MANAGER_DATABASE", "")


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class TranscriptionDatabase:

    def __init__(self) -> None:
        credential = DefaultAzureCredential()
        self.client = CosmosClient(COSMOS_ENDPOINT, credential)  #type: ignore
        self.database_name = DATABASE_NAME

    async def load_managers_names(self):
        """
        Load list of managers
        """
        async with self.client as cosmos_client:
            database = cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("evaluation")
            query = "SELECT * FROM c"
        return [item["name"] async for item in container.query_items(query=query)]

    async def load_manager_data(self, manager_name: str) -> Dict:
        """
        Loads manager data from the evaluation container
        in the Cosmos DB based on the given manager name.
        Args:
            manager_name (str): The name of the manager.
        Returns:
            Dict: A dictionary containing the loaded manager data.
        Raises:
            Exception: If an error occurs while loading the manager data.
        """

        async with self.client as cosmos_client:
            try:
                database = cosmos_client.get_database_client(self.database_name)
                container = database.get_container_client("evaluation")
                query = "SELECT * FROM c WHERE c.manager = @manager_name"
                parameters = [{"name": "@manager_name", "value": manager_name}]
                manager_dict = {}

                async for item in container.query_items(query=query, parameters=parameters):  #type: ignore
                    mgr_name = item["manager"]
                    specialist_name = item["assistant"]

                    if mgr_name not in manager_dict:
                        manager_dict[mgr_name] = {
                            "name": mgr_name,
                            "role": item.get("role", "Gerente"),
                            "specialists": {},
                        }

                    if specialist_name not in manager_dict[mgr_name]["specialists"]:
                        manager_dict[mgr_name]["specialists"][specialist_name] = {
                            "name": specialist_name,
                            "role": item.get("role", "Especialista"),
                            "transcriptions": 0,
                            "total_performance": 0,
                        }

                    try:
                        specialist_data = manager_dict[mgr_name]["specialists"][specialist_name]
                        specialist_data["transcriptions"] += 1
                        specialist_data["total_performance"] += item.get("evaluation", {}).get("pontuacao-total", 0)
                    except Exception as exc:
                        logger.error("Error loading manager data: %s", str(exc))
                        continue

                for mgr_name, manager_data in manager_dict.items():
                    specialists = []
                    for specialist_name, specialist_data in manager_data["specialists"].items():
                        specialist = {
                            "name": specialist_data["name"],
                            "role": specialist_data["role"],
                            "transcriptions": specialist_data["transcriptions"],
                            "performance": specialist_data["total_performance"] / specialist_data["transcriptions"],
                        }
                        specialists.append(specialist)

                    manager_data["specialists"] = specialists
                    manager_data["transcriptions"] = sum(
                        specialist["transcriptions"] for specialist in specialists
                    )
                    manager_data["performance"] = sum(
                        specialist["performance"] for specialist in specialists
                    ) / len(specialists)

                return manager_dict

            except azure_exceptions.ServiceRequestError as exc:
                return {"Error connecting to Azure": str(exc)}

    async def load_transcription_data(self, specialist_name: str) -> List[Dict]:
        """
        Loads transcription data for a given specialist name.
        Args:
            specialist_name (str): The name of the specialist.
        Returns:
            List[Dict]: A list of dictionaries containing the transcription data for the specialist.
        """

        async with self.client as cosmos_client:
            try:
                database = cosmos_client.get_database_client(self.database_name)
                container = database.get_container_client("evaluation")
                query = "SELECT * FROM c WHERE c.assistant = @assistant_name"
                parameters = [{"name": "@assistant_name", "value": specialist_name}]

                specialist_transcriptions = []
                async for item in container.query_items(query=query, parameters=parameters):  # type: ignore
                    try:
                        specialist_transcription = {
                            "id": item["id"],
                            "filename": item["filename"],
                            "content": item["transcription"],
                            "classification": item.get("evaluation", {}).get(
                                "classificao", "Não classificado"
                            ),
                            "successfulCall": item.get("is_valid_call", "NÃO"),
                            "identifiedClient": "Não",
                            "improvementSugestion": item.get("evaluation", {}).get("sugestoes-melhoria", {}),
                            "summaryData": item.get("evaluation", {}).get("items", [])
                        }
                        specialist_transcriptions.append(specialist_transcription)
                    except Exception as exc:
                        logger.error("Error loading transcription data: %s", str(exc))
                        continue

                return specialist_transcriptions

            except azure_exceptions.ServiceRequestError as exc:
                return [{"Error connecting to Azure": str(exc)}]
