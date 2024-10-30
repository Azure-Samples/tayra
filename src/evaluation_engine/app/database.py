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

    async def load_evaluation_for_manager(self, manager_name: str):
        """
        Load list of managers
        """
        async with self.client as cosmos_client:
            database = cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("evaluation")
            query = "SELECT * FROM c"
        return [item["name"] async for item in container.query_items(query=query)]

    async def load_evaluation_for_analyst(self, analyst_name: str):
        """
        Load list of managers
        """
        async with self.client as cosmos_client:
            database = cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("evaluation")
            query = "SELECT * FROM c"
        return [item["name"] async for item in container.query_items(query=query)]

    async def add_human_score(self, analyst_name: str):
        """
        Load list of managers
        """
        async with self.client as cosmos_client:
            database = cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client("evaluation")
            query = "SELECT * FROM c"
        return [item["name"] async for item in container.query_items(query=query)]

    async def set_normalized_score(self, transcription_id: str, normalized_score: float) -> None:
        """
        Sets the normalized score for a given transcription ID.
        Args:
            transcription_id (str): The ID of the transcription.
            normalized_score (float): The normalized score to set.
        Raises:
            Exception: If an error occurs while setting the normalized score.
        """

        async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as cosmos_client:
            try:
                database = cosmos_client.get_database_client(DATABASE_NAME)
                container = database.get_container_client("evaluation")
                item = await container.read_item(item=transcription_id, partition_key=transcription_id)

                # Update the item's score
                item["normalized_score"] = normalized_score

                # Replace the item in the container
                await container.replace_item(item=transcription_id, body=item)

            except azure_exceptions.ServiceRequestError as exc:
                raise Exception(f"Error connecting to Azure: {str(exc)}")
