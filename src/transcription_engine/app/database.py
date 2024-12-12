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

from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions


COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.getenv("COSMOS_KEY", "")
COSMOS_DB_TRANSCRIPTION = os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job")


logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class TranscriptionDatabase:

    def __init__(self) -> None:
        self.database_name = COSMOS_DB_TRANSCRIPTION

    async def load_managers_names(self):
        """
        Load list of managers
        """
        async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as client:
            database = client.get_database_client(self.database_name)
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
        manager_name = str(manager_name).upper()
        async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as client:
            try:
                database = client.get_database_client(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
                await database.read()
            except exceptions.CosmosResourceNotFoundError:
                await client.create_database(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
            container = database.get_container_client(os.getenv("CONTAINER_NAME", "transcriptions"))
            query = "SELECT * FROM c"
            managers = [
                item
                async for item in container.query_items(query=query)
            ]  #type: ignore

        for manager in managers:
            condition = str(manager["name"]).upper() == manager_name
            if condition:
                return manager

    async def load_transcription_data(self, specialist_id: str) -> List[Dict]:
        """
        Loads transcription data for a given specialist name.
        Args:
            specialist_name (str): The name of the specialist.
        Returns:
            List[Dict]: A list of dictionaries containing the transcription data for the specialist.
        """
        async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as client:
            try:
                database = client.get_database_client(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
                await database.read()
            except exceptions.CosmosResourceNotFoundError:
                await client.create_database(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
            container = database.get_container_client(os.getenv("CONTAINER_NAME", "transcriptions"))
            query = "SELECT * FROM c"
            managers = [
                item
                async for item in container.query_items(query=query)
            ]  #type: ignore

        specialists = []
        for manager in managers:
            for specialist in manager["assistants"]:
                condition = str(specialist["name"]).upper() == specialist_id.upper()
                if condition:
                    specialists.append(specialist)
        return specialists

    async def load_transcriptions(self) -> List[Dict]:
        """
        Loads transcription data for a given specialist name.
        Args:
            specialist_name (str): The name of the specialist.
        Returns:
            List[Dict]: A list of dictionaries containing the transcription data for the specialist.
        """
        async with CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY) as cosmos_client:
            try:
                database = cosmos_client.get_database_client(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
                await database.read()
            except exceptions.CosmosResourceNotFoundError:
                await cosmos_client.create_database(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
            container = database.get_container_client(os.getenv("CONTAINER_NAME", "transcriptions"))
            query = "SELECT * FROM c"

            response = [
                item
                async for item
                in container.query_items(query=query)
            ]
        return response
