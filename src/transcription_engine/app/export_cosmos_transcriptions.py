"""Utility script to export transcription documents from Cosmos DB.

The script connects to the configured Cosmos DB container and flattens every
transcription entry into a JSON Lines file that only contains the filename,
transcription text, and metadata fields. Optional filters allow narrowing the
export to a specific manager or specialist.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterable

from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions
from azure.identity.aio import DefaultAzureCredential
from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv())
DEFAULT_DB_NAME = os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job")
DEFAULT_CONTAINER_NAME = os.getenv("CONTAINER_NAME", "transcriptions")


def _str_to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes"}


def _should_use_aad() -> bool:
    flag = os.getenv("COSMOS_USE_AAD")
    if flag is not None:
        return _str_to_bool(flag, False)
    return not bool(os.getenv("COSMOS_KEY"))


async def _get_cosmos_client() -> tuple[CosmosClient, DefaultAzureCredential | None]:
    endpoint = os.getenv("COSMOS_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError("COSMOS_ENDPOINT environment variable is required")

    if _should_use_aad():
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        return CosmosClient(endpoint, credential=credential), credential

    key = os.getenv("COSMOS_KEY", "").strip()
    if not key:
        raise RuntimeError("COSMOS_KEY must be provided when COSMOS_USE_AAD is false")
    return CosmosClient(endpoint, key), None


async def _iterate_documents(container, manager: str | None) -> AsyncIterator[Dict[str, Any]]:
    query = "SELECT * FROM c"
    parameters = []
    if manager:
        query = "SELECT * FROM c WHERE c.name = @manager"
        parameters = [{"name": "@manager", "value": manager}]

    result_iterable = container.query_items(
        query=query,
        parameters=parameters,
        feed_options={"enableCrossPartitionQuery": True},
    )

    async for item in result_iterable:
        yield item


def _iter_transcription_rows(
    document: Dict[str, Any],
    specialist_name: str | None,
    only_valid: bool,
) -> Iterable[Dict[str, Any]]:
    assistants = document.get("assistants") or []
    for assistant in assistants:
        if specialist_name and assistant.get("name") != specialist_name:
            continue
        for transcription in assistant.get("transcriptions", []):
            if only_valid and transcription.get("is_valid_call") != "YES":
                continue
            yield {
                "filename": transcription.get("filename"),
                "transcription": transcription.get("transcription"),
                "metadata": transcription.get("metadata", {}),
            }


async def export_transcriptions(args) -> Path:
    client, credential = await _get_cosmos_client()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        database = client.get_database_client(args.database)
        try:
            await database.read()
        except exceptions.CosmosResourceNotFoundError as exc:
            raise RuntimeError(
                f"Database '{args.database}' not found at {client.client_connection.url_connection}"
            ) from exc

        container = database.get_container_client(args.container)
        try:
            await container.read()
        except exceptions.CosmosResourceNotFoundError as exc:
            raise RuntimeError(
                f"Container '{args.container}' not found in database '{args.database}'"
            ) from exc

        rows_written = 0
        with output_path.open("w", encoding="utf-8") as handle:
            async for document in _iterate_documents(container, args.manager):
                for row in _iter_transcription_rows(document, args.specialist, args.only_valid):
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    rows_written += 1

        print(f"Export complete: {rows_written} rows written to {output_path}")
        return output_path
    finally:
        await client.close()
        if credential:
            await credential.close()


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Export Cosmos DB transcriptions to JSONL")
    parser.add_argument(
        "--output",
        default="cosmos_transcriptions.jsonl",
        help="Destination JSON Lines file",
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DB_NAME,
        help="Cosmos DB database name",
    )
    parser.add_argument(
        "--container",
        default=DEFAULT_CONTAINER_NAME,
        help="Cosmos DB container name",
    )
    parser.add_argument(
        "--manager",
        help="Filter export to a specific manager name",
    )
    parser.add_argument(
        "--specialist",
        help="Filter export to a specific specialist name",
    )
    parser.add_argument(
        "--only-valid",
        action="store_true",
        help="Include only entries marked as valid calls",
    )

    args = parser.parse_args()
    await export_transcriptions(args)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
