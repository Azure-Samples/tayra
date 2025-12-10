"""Data access helper for the classification engine FastAPI app."""

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from azure.cosmos import exceptions
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.getenv("COSMOS_KEY", "")
COSMOS_DB_NAME = os.getenv("COSMOS_DB_TRANSCRIPTION", "tayradb")
TRANSCRIPTIONS_CONTAINER = os.getenv("CONTAINER_NAME", "transcriptions")
CLASSIFICATION_CONTAINER = os.getenv("COSMOS_CLASSIFICATION_CONTAINER", "classifications")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


class ClassificationDatabase:
    """Convenience wrapper around Cosmos DB queries used by the API."""

    def __init__(self) -> None:
        if not COSMOS_ENDPOINT:
            raise RuntimeError("COSMOS_ENDPOINT is not configured for classification database access.")
        self.database_name = COSMOS_DB_NAME
        self.transcriptions_container = TRANSCRIPTIONS_CONTAINER
        self.classifications_container = CLASSIFICATION_CONTAINER
        self.use_aad_auth = self._should_use_aad_auth()
        self._aad_credential: Optional[DefaultAzureCredential] = None
        if not self.use_aad_auth and not COSMOS_KEY:
            raise RuntimeError(
                "COSMOS_KEY is not configured. Set COSMOS_USE_AAD=true to rely on AAD authentication."
            )

    def _should_use_aad_auth(self) -> bool:
        flag = os.getenv("COSMOS_USE_AAD", "")
        if flag:
            return flag.lower() in {"1", "true", "yes"}
        return not bool(COSMOS_KEY)

    def _get_cosmos_client(self) -> CosmosClient:
        if self.use_aad_auth:
            if not self._aad_credential:
                self._aad_credential = DefaultAzureCredential(
                    exclude_interactive_browser_credential=True
                )
            return CosmosClient(COSMOS_ENDPOINT, credential=self._aad_credential)
        return CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)

    async def _get_container(self, client: CosmosClient, container_name: str):
        database = client.get_database_client(self.database_name)
        try:
            await database.read()
        except exceptions.CosmosResourceNotFoundError:
            await client.create_database(self.database_name)
            database = client.get_database_client(self.database_name)
        return database.get_container_client(container_name)

    async def load_managers_names(self) -> List[str]:
        async with self._get_cosmos_client() as client:
            container = await self._get_container(client, self.transcriptions_container)
            query = "SELECT c.name FROM c"
            return [item.get("name", "") async for item in container.query_items(query=query)]

    async def load_manager_data(self, manager_name: str) -> Optional[Dict]:
        manager_key = manager_name.upper()
        async with self._get_cosmos_client() as client:
            container = await self._get_container(client, self.transcriptions_container)
            query = "SELECT * FROM c"
            managers = [item async for item in container.query_items(query=query)]
        for manager in managers:
            if str(manager.get("name", "")).upper() == manager_key:
                return manager
        return None

    async def load_transcription_data(self, specialist_id: str) -> List[Dict]:
        specialist_key = specialist_id.upper()
        async with self._get_cosmos_client() as client:
            container = await self._get_container(client, self.transcriptions_container)
            query = "SELECT * FROM c"
            managers = [item async for item in container.query_items(query=query)]
        specialists: List[Dict] = []
        for manager in managers:
            for specialist in manager.get("assistants", []):
                if str(specialist.get("name", "")).upper() == specialist_key:
                    specialists.append(specialist)
        return specialists

    async def load_transcriptions(self) -> List[Dict]:
        async with self._get_cosmos_client() as client:
            container = await self._get_container(client, self.transcriptions_container)
            query = "SELECT * FROM c"
            return [item async for item in container.query_items(query=query)]

    async def load_transcription_by_filename(self, file_name: str) -> Optional[Dict[str, Any]]:
        normalized = file_name.strip().lower()
        if not normalized:
            return None
        async with self._get_cosmos_client() as client:
            container = await self._get_container(client, self.transcriptions_container)
            query = (
                "SELECT t AS transcription "
                "FROM c JOIN a IN c.assistants JOIN t IN a.transcriptions "
                "WHERE (IS_DEFINED(t.metadata.file_name) AND LOWER(t.metadata.file_name) = @file) "
                "OR (IS_DEFINED(t.filename) AND LOWER(t.filename) = @file)"
            )
            parameters = [{"name": "@file", "value": normalized}]
            async for item in container.query_items(query=query, parameters=parameters):
                transcription = item.get("transcription", {}) or {}
                metadata = transcription.get("metadata") or {}
                return {
                    "metadata": metadata,
                    "file_name": metadata.get("file_name")
                    or transcription.get("filename"),
                    "is_valid_call": transcription.get("is_valid_call"),
                    "transcription": transcription.get("transcription"),
                }
        return None

    async def load_classification_records(
        self, *, manager: Optional[str] = None, specialist: Optional[str] = None
    ) -> List[Dict]:
        async with self._get_cosmos_client() as client:
            container = await self._get_container(client, self.classifications_container)
            filters = []
            parameters = []
            if manager:
                filters.append("c.manager_name = @manager")
                parameters.append({"name": "@manager", "value": manager})
            if specialist:
                filters.append("c.specialist_name = @specialist")
                parameters.append({"name": "@specialist", "value": specialist})
            where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
            query = f"SELECT * FROM c{where_clause}"
            return [
                item
                async for item in container.query_items(
                    query=query,
                    parameters=parameters if parameters else None,
                )
            ]
