"""Batch classify Cosmos transcriptions with Microsoft Agent Framework."""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
from uuid import uuid4

from azure.cosmos import PartitionKey
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.core.pipeline import policies
from dotenv import find_dotenv, load_dotenv

try:
    from agent_framework.azure import AzureAIClient
    from agent_framework.exceptions import ServiceResponseException
except ImportError as exc:  # pragma: no cover - defensive guard for missing dependency
    raise ImportError(
        "Install agent-framework (pip install agent-framework) to run the"
        " call center classification agent."
    ) from exc


load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class CosmosTranscriptionRepository:
    """Utility to stream and update transcription documents from Cosmos DB."""

    def __init__(self) -> None:
        self.endpoint = os.getenv("COSMOS_ENDPOINT", "")
        self.database_name = os.getenv("COSMOS_DB_TRANSCRIPTION", "tayradb")
        self.container_name = os.getenv("CONTAINER_NAME", "transcriptions")
        self.classification_container_name = os.getenv(
            "COSMOS_CLASSIFICATION_CONTAINER", "classifications"
        )
        partition_key = os.getenv("COSMOS_CLASSIFICATION_PARTITION_KEY", "/parent_document_id").strip()
        if partition_key and not partition_key.startswith("/"):
            partition_key = f"/{partition_key}"
        self.classification_partition_key = partition_key or "/parent_document_id"
        self.cosmos_key = os.getenv("COSMOS_KEY", "")
        self.use_aad_auth = self._should_use_aad_auth()
        self._aad_credential: Optional[DefaultAzureCredential] = None
        self._classification_container_ready = False

    def _should_use_aad_auth(self) -> bool:
        flag = os.getenv("COSMOS_USE_AAD", "")
        if flag:
            return flag.lower() in {"1", "true", "yes"}
        return not bool(self.cosmos_key)

    def _get_cosmos_client(self) -> CosmosClient:
        if self.use_aad_auth:
            if not self._aad_credential:
                self._aad_credential = DefaultAzureCredential(
                    exclude_interactive_browser_credential=True
                )
            return CosmosClient(self.endpoint, credential=self._aad_credential)
        if not self.cosmos_key:
            raise RuntimeError(
                "COSMOS_KEY is not configured and AAD auth is disabled."
                " Set COSMOS_USE_AAD=true or provide a key to classify transcriptions."
            )
        return CosmosClient(self.endpoint, credential=self.cosmos_key)

    async def iter_documents(self) -> AsyncIterator[Dict[str, Any]]:
        async with self._get_cosmos_client() as client:
            database = client.get_database_client(self.database_name)
            container = database.get_container_client(self.container_name)
            async for document in container.read_all_items():
                yield document

    async def replace_document(self, document: Dict[str, Any]) -> None:
        async with self._get_cosmos_client() as client:
            database = client.get_database_client(self.database_name)
            container = database.get_container_client(self.container_name)
            await container.replace_item(item=document["id"], body=document)

    async def _ensure_classification_container(self) -> None:
        if self._classification_container_ready:
            return
        async with self._get_cosmos_client() as client:
            database = client.get_database_client(self.database_name)
            await database.create_container_if_not_exists(
                id=self.classification_container_name,
                partition_key=PartitionKey(path=self.classification_partition_key),
            )
        self._classification_container_ready = True

    async def save_classification_record(
        self,
        *,
        parent_document_id: str,
        manager_name: str,
        specialist_name: str,
        transcription: Dict[str, Any],
        classification: Dict[str, Any],
        classification_ts_utc: str,
    ) -> None:
        base_identifier = (
            transcription.get("id")
            or transcription.get("filename")
            or transcription.get("transcription_id")
            or uuid4().hex
        )
        logging.info("Saving classification record for transcription %s", base_identifier)
        record_id = f"{parent_document_id}:{base_identifier}:{uuid4().hex}"
        record = {
            "id": record_id,
            "parent_document_id": parent_document_id,
            "manager_name": manager_name,
            "specialist_name": specialist_name,
            "transcription_id": transcription.get("id"),
            "filename": transcription.get("filename"),
            "is_valid_call": transcription.get("is_valid_call"),
            "classification": classification,
            "classification_ts_utc": classification_ts_utc,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        transcript_text = transcription.get("transcription")
        if transcript_text:
            record["transcription"] = transcript_text

        await self._ensure_classification_container()
        async with self._get_cosmos_client() as client:
            database = client.get_database_client(self.database_name)
            container = database.get_container_client(self.classification_container_name)
            await container.upsert_item(body=record)

    async def close(self) -> None:
        if self._aad_credential:
            await self._aad_credential.close()


class CallClassificationAgent:
    """Azure AI Agent wrapper configured for Cemex call classification."""

    RESPONSE_SCHEMA = """
    {
        "label": "order_creation | order_modification | order_follow_up | other",
        "confidence": 0.0-1.0,
        "reason": "short sentence referencing the transcript",
        "next_action": "automation_hint for downstream workflows"
    }
    """.strip()

    def __init__(self) -> None:
        self.agent_name = os.getenv("CALL_CLASSIFIER_AGENT_NAME", "CemexCallClassifier")
        self.use_latest_version = os.getenv("CALL_CLASSIFIER_USE_LATEST", "true").lower() in {
            "true",
            "1",
            "yes",
        }
        self._credential: Optional[AzureCliCredential] = None
        self._endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
        self._deployment_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "")
        self._project_client: Optional[AIProjectClient] = None
        self._client: Optional[AzureAIClient] = None
        self._agent_cm = None
        self._agent = None
        self.max_retries = int(os.getenv("CALL_CLASSIFIER_MAX_RETRIES", "5"))
        self.retry_backoff_seconds = float(os.getenv("CALL_CLASSIFIER_RETRY_BACKOFF", "5"))

    async def __aenter__(self):
        self._credential = AzureCliCredential()
        await self._credential.__aenter__()
        if not self._endpoint or not self._deployment_name:
            raise RuntimeError(
                "AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME must be set for"
                " the CallClassificationAgent."
            )

        headers_policy = policies.HeadersPolicy(headers={"Accept-Encoding": "identity"})
        self._project_client = AIProjectClient(
            endpoint=self._endpoint,
            credential=self._credential,
            headers_policy=headers_policy,
        )

        self._client = AzureAIClient(
            project_client=self._project_client,
            agent_name=self.agent_name,
            model_deployment_name=self._deployment_name,
            async_credential=self._credential,
            use_latest_version=self.use_latest_version,
        )
        self._agent_cm = self._client.create_agent(
            name=self.agent_name,
            instructions=self._build_instructions(),
        )
        self._agent = await self._agent_cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, exc_tb):
        if self._agent_cm:
            await self._agent_cm.__aexit__(exc_type, exc, exc_tb)
        if self._client:
            await self._client.close()
        if self._project_client:
            await self._project_client.close()
        if self._credential:
            await self._credential.__aexit__(exc_type, exc, exc_tb)
        self._agent_cm = None
        self._agent = None
        self._project_client = None
        self._client = None

    def _build_instructions(self) -> str:
        return (
            "You are a quality control assistant for Cemex customer service calls in the United"
            " States. Analyze each transcript carefully, then classify the call intent using the"
            " allowed labels (order_creation, order_modification, order_follow_up, other)."
            " Output a compact JSON object that matches this schema exactly:"
            f" {self.RESPONSE_SCHEMA}."
            " Assess whether the caller wanted to create a new order, modify an existing one, or"
            " follow up on a prior request. Use 'other' if the transcript is unrelated or lacks"
            " enough context. Keep confidence between 0 and 1."
        )

    async def classify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._agent:
            raise RuntimeError(
                "Agent not initialized. Use 'async with CallClassificationAgent()' before classifying."
            )

        prompt = self._build_prompt(payload)
        response = await self._run_with_retry(prompt)
        output_text = self._ensure_text_response(response)
        cleaned_text = self._strip_markdown_fence(output_text)
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as exc:
            logging.error("Agent response was not JSON: %s", output_text)
            raise RuntimeError("Classification agent returned invalid JSON") from exc

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return (
            "Context about the project: The goal is to automatically classify customer service"
            " calls for Cemex USA to improve reporting accuracy and operational efficiency."
            "\n\n"
            "Return JSON that matches this schema exactly (do not include extra text):\n"
            f"{self.RESPONSE_SCHEMA}\n\n"
            "Transcript metadata:\n"
            f"Manager: {payload.get('manager_name', 'UNKNOWN')}\n"
            f"Specialist: {payload.get('specialist_name', 'UNKNOWN')}\n"
            f"Filename: {payload.get('filename')}\n"
            f"IsValidCall: {payload.get('is_valid_call')}\n"
            "Transcript:\n"
            f"""{payload.get('transcription', '').strip()}"""
        )

    async def _run_with_retry(self, prompt: str) -> Any:
        attempt = 0
        while True:
            try:
                return await self._agent.run(prompt)
            except ServiceResponseException as exc:
                attempt += 1
                if not self._should_retry(exc, attempt):
                    raise
                delay = self.retry_backoff_seconds * (2 ** (attempt - 1))
                logging.warning(
                    "Azure AI agent rate-limited (attempt %s/%s). Retrying in %.1fs",
                    attempt,
                    self.max_retries,
                    delay,
                )
                await asyncio.sleep(delay)

    def _should_retry(self, exc: ServiceResponseException, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
        message = str(exc).lower()
        if "too many requests" in message or "429" in message:
            return True
        return False

    def _ensure_text_response(self, agent_response: Any) -> str:
        if isinstance(agent_response, str):
            return agent_response.strip()
        response_text = getattr(agent_response, "text", None)
        if isinstance(response_text, str) and response_text.strip():
            return response_text.strip()
        if hasattr(agent_response, "output_text") and agent_response.output_text:
            return agent_response.output_text.strip()
        if hasattr(agent_response, "output") and agent_response.output:
            content = agent_response.output[0].content[0]
            if hasattr(content, "text"):
                return content.text.strip()
        if hasattr(agent_response, "messages") and agent_response.messages:
            message_text = "\n".join(
                msg.text.strip()
                for msg in agent_response.messages
                if hasattr(msg, "text") and isinstance(msg.text, str)
            ).strip()
            if message_text:
                return message_text
        value_payload = getattr(agent_response, "value", None)
        if value_payload is not None:
            if isinstance(value_payload, str):
                return value_payload.strip()
            # Agent framework populates value for structured outputs; serialize so JSON loads succeeds.
            return json.dumps(value_payload)
        raise RuntimeError("Unable to read text from Azure AI agent response. Check SDK version.")

    def _strip_markdown_fence(self, text: str) -> str:
        stripped = text.strip()
        if not stripped.startswith("```"):
            return stripped

        if stripped.count("```") < 2:
            return stripped

        # remove opening fence (``` or ```json)
        without_open = stripped[3:]
        newline_idx = without_open.find("\n")
        if newline_idx == -1:
            return stripped
        language = without_open[:newline_idx].strip().lower()
        payload_start = newline_idx + 1
        if language and language in {"json", "javascript"}:
            inner = without_open[payload_start:]
        else:
            inner = without_open

        # remove closing fence
        closing_index = inner.rfind("```")
        if closing_index != -1:
            inner = inner[:closing_index]
        return inner.strip()


class ClassificationPipeline:
    """Coordinates Cosmos ingestion and per-transcription classification."""

    def __init__(
        self,
        *,
        manager_name: Optional[str] = None,
        specialist_name: Optional[str] = None,
        limit: Optional[int] = None,
        skip_already_classified: bool = False,
        only_valid_calls: bool = True,
    ) -> None:
        self.repository = CosmosTranscriptionRepository()
        self.manager_filter = manager_name.strip().upper() if manager_name else None
        self.specialist_filter = (
            specialist_name.strip().upper() if specialist_name else None
        )
        self.limit = limit if limit and limit > 0 else None
        self.skip_already_classified = skip_already_classified
        self.only_valid_calls = only_valid_calls
        self._processed = 0

    async def run(self) -> int:
        try:
            async with CallClassificationAgent() as classifier:
                async for document in self.repository.iter_documents():

                    updated, should_stop = await self._classify_document(document, classifier)
                    if updated:
                        await self.repository.replace_document(document)
                    if should_stop:
                        break
        finally:
            await self.repository.close()
        return self._processed

    def _limit_reached(self) -> bool:
        return self.limit is not None and self._processed >= self.limit

    async def _classify_document(
        self, document: Dict[str, Any], classifier: CallClassificationAgent
    ) -> Tuple[bool, bool]:
        changed = False
        manager_name = document.get("name", "UNKNOWN")
        manager_key = str(manager_name).upper()
        if self.manager_filter and manager_key != self.manager_filter:
            return False, False
        parent_document_id = str(document.get("id") or manager_name)
        assistants: List[Dict[str, Any]] = document.get("assistants", [])
        should_stop = False

        for assistant in assistants:
            specialist_name = assistant.get("name", "UNKNOWN")
            specialist_key = str(specialist_name).upper()
            if self.specialist_filter and specialist_key != self.specialist_filter:
                continue
            for transcription in assistant.get("transcriptions", []):
                if self.only_valid_calls and transcription.get("is_valid_call") != "YES":
                    logging.info(
                        "Skipping invalid call transcription %s/%s (%s)",
                        manager_name,
                        specialist_name,
                        transcription.get("filename") or transcription.get("id"),
                    )
                    continue
                metadata = transcription.setdefault("metadata", {})
                if self.skip_already_classified and metadata.get("classification"):
                    logging.info(
                        "Skipping already classified transcription %s/%s (%s)",
                        manager_name,
                        specialist_name,
                        transcription.get("filename") or transcription.get("id"),
                    )
                    continue

                payload = {
                    "manager_name": manager_name,
                    "specialist_name": specialist_name,
                    "filename": transcription.get("filename") or transcription.get("id"),
                    "transcription": transcription.get("transcription", ""),
                    "is_valid_call": transcription.get("is_valid_call"),
                }
                logging.info(
                    "Classifying %s/%s (%s)",
                    manager_name,
                    specialist_name,
                    payload["filename"],
                )
                classification = await classifier.classify(payload)
                classification_ts = datetime.now(timezone.utc).isoformat()
                metadata["classification"] = classification.get("label")
                metadata["classification_confidence"] = classification.get("confidence")
                metadata["classification_reason"] = classification.get("reason")
                metadata["classification_next_action"] = classification.get("next_action")
                metadata["classification_ts_utc"] = classification_ts
                transcription["metadata"] = metadata
                changed = True
                self._processed += 1
                await self.repository.save_classification_record(
                    parent_document_id=parent_document_id,
                    manager_name=manager_name,
                    specialist_name=specialist_name,
                    transcription=transcription,
                    classification=classification,
                    classification_ts_utc=classification_ts,
                )
                logging.info(
                    "Classified %s/%s (%s) as %s",
                    manager_name,
                    specialist_name,
                    transcription.get("filename"),
                    metadata["classification"],
                )
                if self._limit_reached():
                    should_stop = True
                    break
            if should_stop:
                break

        return changed, should_stop


async def main() -> None:
    pipeline = ClassificationPipeline()
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
