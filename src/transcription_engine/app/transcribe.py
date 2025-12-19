import asyncio
import io
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import time
import uuid
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import List

import httpx
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobClient, BlobServiceClient
from dotenv import find_dotenv, load_dotenv

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.append(str(PACKAGE_ROOT))

from app.schemas import TranscriptionJobParams, Transcription, SpecialistItem, ManagerModel

load_dotenv(find_dotenv())
logging.getLogger('azure').setLevel(logging.WARNING)

class BlobTranscriptionProcessor:
    BATCH_SIZE = 50
    SHORT_CALL_TEXT = "Call too short or not answered."

    def __init__(self):
        self.ai_speech_key = os.getenv("AI_SPEECH_KEY", "")
        self.cosmos_endpoint = os.getenv("COSMOS_ENDPOINT", "")
        self.cosmos_key = os.getenv("COSMOS_KEY", "")
        self.storage_connection_string  = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
        self.storage_account_name, self.storage_account_key = self._parse_storage_connection_string(self.storage_connection_string)
        self.use_aad_auth = self._should_use_aad_auth()
        self._aad_credential: DefaultAzureCredential | None = None
        self._log_stream: io.StringIO | None = None
        self.failed_files = set()

    async def __call__(self, params: TranscriptionJobParams):
        """Run the entire processing logic using the provided parameters."""
        listener = await self.init_logger()
        try:
            await self.process_blob_storage(params)
        finally:
            listener.stop()
            if self._aad_credential:
                await self._aad_credential.close()

    async def init_logger(self):
        self._log_stream = io.StringIO()
        log = logging.getLogger()
        que = Queue()
        queue_handler = QueueHandler(que)
        log.addHandler(queue_handler)
        log.setLevel(logging.INFO)
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        buffer_handler = logging.StreamHandler(stream=self._log_stream)
        listener = QueueListener(que, stdout_handler, buffer_handler)
        listener.start()
        logging.debug('Logger has started')
        return listener

    def _short_call_result(self, reason: str) -> dict:
        return {"text": self.SHORT_CALL_TEXT, "short_reason": reason}

    async def get_failed_transcriptions(self):
        database_name = os.getenv("COSMOS_DB_TRANSCRIPTION", "tayradb")
        container_name = os.getenv("CONTAINER_NAME", "transcriptions")
        logging.debug(
            "Loading failed transcriptions (endpoint=%s, database=%s, container=%s, aad=%s)",
            self.cosmos_endpoint,
            database_name,
            container_name,
            self.use_aad_auth,
        )
        try:
            async with self._get_cosmos_client() as client:
                try:
                    database = client.get_database_client(database_name)
                    await database.read()
                except exceptions.CosmosResourceNotFoundError:
                    await client.create_database(database_name)
                    database = client.get_database_client(database_name)

                container = database.get_container_client(container_name)
                failed_items = container.query_items(
                    query="SELECT * FROM c WHERE c.is_valid_call != 'SIM'",
                )

                self.failed_files = {
                    f"{'/'.join(str(os.path.splitext(item.get('filename', ''))[0]).split('/')[-3:])}"
                    async for item in failed_items
                }
        except exceptions.CosmosHttpResponseError as exc:
            logging.error(
                "Cosmos query failed (status=%s activityId=%s message=%s)",
                exc.status_code,
                exc.headers.get('x-ms-activity-id') if exc.headers else 'unknown',
                exc.message,
            )
            raise
        except Exception as exc:
            logging.exception(
                "Unexpected error while loading failed transcriptions from Cosmos (database=%s, container=%s)",
                database_name,
                container_name,
            )
            raise

    async def _process_blob_batch(
        self,
        blob_batch: List[BlobClient]
    ):
        tasks = []
        async with asyncio.TaskGroup() as group:
            for blob_client in blob_batch:
                task = group.create_task(
                    self.transcribe_and_save(blob_client, blob_client.blob_name)
                )
                tasks.append(task)
        return [task.result() for task in tasks]

    def _set_prefix(self, params: TranscriptionJobParams):
        prefix = ""
        if params.manager_name:
            prefix += f"{params.manager_name}/"
            if params.specialist_name:
                prefix += f"{params.specialist_name}/"
        return prefix

    async def _process_batch(self, prefix, checked_transcriptions_cache, results_per_page, params: TranscriptionJobParams):
        counter = 0
        transcription_metadata = []
        async with BlobServiceClient.from_connection_string(self.storage_connection_string) as blob_service_client:
            container_client = blob_service_client.get_container_client(params.origin_container)

            batch = []
            async for blob_page in container_client.list_blobs(results_per_page=results_per_page).by_page():

                async for blob in blob_page:
                    if not await self.is_blob_valid(blob, checked_transcriptions_cache, blob_service_client, params):
                        continue

                    blob_client = container_client.get_blob_client(blob.name)
                    batch.append(blob_client)
                    counter += 1
                    logging.warning("Current batch size: %s. \n", len(batch))

                    if len(batch) >= self.BATCH_SIZE:
                        batch_metadata = await self._process_blob_batch(batch)
                        transcription_metadata.extend(batch_metadata)
                        batch.clear()

                    if counter >= (params.limit or -1) > 1:
                        if batch:
                            batch_metadata = await self._process_blob_batch(batch)
                            transcription_metadata.extend(batch_metadata)
                        break

            if batch:
                batch_metadata = await self._process_blob_batch(batch)
                transcription_metadata.extend(batch_metadata)
                batch.clear()
        return transcription_metadata, counter

    async def process_blob_storage(self, params: TranscriptionJobParams):
        logging.info("Running for manager %s and specialist %s", params.manager_name, params.specialist_name)
        logging.info("Starting transcription process for container %s with limit %s", params.origin_container, params.limit)
        logging.info("Using %s asynchronous semaphores", params.semaphores)
        start_timestamp = datetime.utcnow()
        start_overall = time.perf_counter()
        logging.info("Starting job at %s UTC", start_timestamp.isoformat())

        await self.get_failed_transcriptions()
        checked_transcriptions_cache = {}
        prefix = self._set_prefix(params)

        results_per_page = params.results_per_page
        if not results_per_page:
            results_per_page = self.BATCH_SIZE

        transcription_metadata, counter = await self._process_batch(prefix, checked_transcriptions_cache, results_per_page, params)

        end_timestamp = datetime.utcnow()
        end_overall = time.perf_counter()
        logging.info("Job finished at %s UTC", end_timestamp.isoformat())
        overall_duration = end_overall - start_overall
        human_duration = str(timedelta(seconds=round(overall_duration)))

        logging.info(
            "Processed %s blobs in %.2f seconds (~%s).\n",
            counter,
            overall_duration,
            human_duration,
        )

        metadata = {
            "transcription_duration": overall_duration,
            "transcription_duration_human": human_duration,
            "processed_files": counter,
            "transcriptions": transcription_metadata,
            "started_at_utc": start_timestamp.isoformat(),
            "finished_at_utc": end_timestamp.isoformat(),
        }

        logging.info("Metadata: %s", transcription_metadata)

        run_timestamp = str(time.time())
        output_file = f"metadata-{run_timestamp}.json"
        log_file = f"logs-{run_timestamp}.txt"
        log_data = self._log_stream.getvalue() if self._log_stream else ""
        metadata["log_blob"] = log_file
        metadata_json = json.dumps(metadata, ensure_ascii=True)

        async with BlobServiceClient.from_connection_string(self.storage_connection_string) as blob_service_client:
            metadata_blob_client = blob_service_client.get_blob_client(
            container=params.destination_container, blob=output_file
            )

            await metadata_blob_client.upload_blob(metadata_json, overwrite=True)
            log_blob_client = blob_service_client.get_blob_client(
                container=params.destination_container, blob=log_file
            )
            await log_blob_client.upload_blob(log_data, overwrite=True)
        logging.info("Metadata written to file: %s", output_file)
        logging.info("Finished uploading to blob: %s", output_file)
        logging.info("Log output written to file: %s", log_file)

    async def is_blob_valid(
        self,
        blob,
        checked_transcriptions_cache: dict,
        blob_service_client: BlobServiceClient,
        transcription_params: TranscriptionJobParams
    ) -> bool:
        condition_file = any(blob.name.endswith(ext) for ext in ["mp3", "wav", "ogg"])
        if not condition_file:
            logging.warning("Skipping blob %s since it is not a wav or mp3 file.\n", blob.name)
            return False

        if transcription_params.manager_name and transcription_params.manager_name not in blob.name:
            logging.warning(
                "Skipping blob %s since it does not belong to manager %s.\n",
                blob.name,
                transcription_params.manager_name,
            )
            return False

        if transcription_params.specialist_name and transcription_params.specialist_name not in blob.name:
            logging.warning(
                "Skipping blob %s since it does not belong to specialist %s.\n",
                blob.name,
                transcription_params.specialist_name,
            )
            return False

        blob_path = "/".join(str(os.path.splitext(blob.name)[0]).split("/")[-3:])
        if transcription_params.only_failed and blob_path not in self.failed_files:
            logging.warning("Skipping blob %s since it is not a valid file.\n", blob.name)
            return False

        if transcription_params.use_cache:
            if blob_path in checked_transcriptions_cache:
                transcription_result = checked_transcriptions_cache[blob_path]
            else:
                transcription_result = await self.check_finished_transcriptions(
                    blob_service_client, transcription_params.destination_container, blob.name
                )
                checked_transcriptions_cache[blob_path] = transcription_result

            if transcription_result is not None:
                logging.info("Skipping blob %s as it has already been transcribed.\n", blob.name)
                return False

        return True

    async def transcribe_and_save(
        self,
        blob_client: BlobClient,
        blob_name: str
    ):
        try:
            start_transcription = time.time()
            logging.info("Transcribing blob %s at %s", blob_name, start_transcription)

            download_stream = await blob_client.download_blob()
            file_stream = await download_stream.read()

            transcription_result = await self.transcribe_file(blob_client, blob_name, io.BytesIO(file_stream))
            logging.info("Transcribing blob %s took %s", blob_name, time.time() - start_transcription)

            transcription_text = transcription_result.get("text", self.SHORT_CALL_TEXT)
            short_reason = transcription_result.get("short_reason")
            blob_properties = await blob_client.get_blob_properties()
            transcription_metadata = {
                "file_name": str(blob_name).lower().replace(" ", "_"),
                "file_size": blob_properties.size,
                "transcription_duration": time.time() - start_transcription,
            }
            if short_reason:
                transcription_metadata["short_reason"] = short_reason
                logging.info("Blob %s marked as short call due to %s", blob_name, short_reason)
            logging.info("Metadata for blob %s: %s", blob_name, transcription_metadata)

            start_saving = time.time()
            await self.save_transcription(
                blob_name,
                transcription_text,
                transcription_metadata,
                short_reason=short_reason,
            )

            logging.debug("Transcription result for %s: %s", blob_name, transcription_text)
            return {
                "file_name": blob_name,
                "file_size": blob_properties.size,
                "saving_duration": time.time() - start_saving,
            }
        except Exception as exc:
            logging.error("Error processing blob %s: %s", blob_name, exc)
            raise exc

    async def check_finished_transcriptions(
        self,
        blob_service_client: BlobServiceClient, destination_container: str, blob_name: str
    ):
        cache_file_name = "/".join(str(os.path.splitext(blob_name)[0]).split("/")[-3:])
        cache_blob_path = f"{cache_file_name}/transcription.txt"

        cache_blob_client = blob_service_client.get_blob_client(
            container=destination_container, blob=cache_blob_path
        )

        try:
            download_stream = await cache_blob_client.download_blob()
            downloaded_blob = await download_stream.readall()
            return {"text": downloaded_blob.decode("utf-8")}
        except Exception as exc:
            logging.warning("No cached transcription found for blob %s. Exception: %s", blob_name, exc)
            return None

    async def transcribe_file(self, blob_client, file_name: str, file_data: io.BytesIO, sem: int = 20):
        sas_url = self._generate_blob_sas_url(blob_client)
        if not sas_url:
            logging.error("Unable to generate SAS URL for blob %s", file_name)
            return self._short_call_result("sas_generation_failed")

        speech_url = self._build_speech_transcription_url()
        if not speech_url:
            logging.error("AI_SPEECH_URL is not configured. Skipping blob %s", file_name)
            return self._short_call_result("missing_endpoint")

        payload = self._build_batch_transcription_payload(file_name, sas_url)
        if os.getenv("CHANGE_BASE_MODEL"):
            payload["model"] = {"self": os.getenv("CHANGE_BASE_MODEL")}
            payload["properties"]["wordLevelTimestampsEnabled"] = "false"

        headers = {
            "Ocp-Apim-Subscription-Key": self.ai_speech_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with asyncio.Semaphore(sem):
            async with httpx.AsyncClient(timeout=None) as client:
                try:
                    response = await client.post(speech_url, headers=headers, json=payload)
                    response.raise_for_status()
                    job_location = (
                        response.headers.get("Operation-Location")
                        or response.headers.get("operation-location")
                        or response.headers.get("Location")
                        or response.headers.get("location")
                    )
                    if not job_location:
                        logging.error("Speech batch job missing Location header for %s", file_name)
                        return self._short_call_result("missing_location")

                    normalized_location = self._normalize_job_location(job_location)

                    job_result = await self._poll_transcription_job(client, normalized_location, headers)
                    model_name = job_result.get("model")
                    logging.info("Model being used: %s", model_name or "unknown")
                    status = job_result.get("status")
                    logging.info("Speech batch job status for %s: %s", file_name, status)

                    if status != "Succeeded":
                        error_message = job_result.get("error", {}).get("message", "batch_failed")
                        logging.error("Speech batch job failed for %s: %s", file_name, error_message)
                        return self._short_call_result("batch_failed")

                    transcript_text = await self._download_batch_transcript(client, job_result, headers)
                    if not transcript_text:
                        return self._short_call_result("empty_transcript")

                    return {"text": transcript_text}
                except httpx.NetworkError as exc:
                    logging.error("Network Error: %s. Trying Again.", str(exc))
                    await asyncio.sleep(0.5)
                    return await self.transcribe_file(blob_client, file_name, file_data)
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code if exc.response else None
                    if status_code in [503, 429, 500, 408, 499]:
                        logging.error("Server error %s: %s. Trying Again.", status_code, str(exc))
                        await asyncio.sleep(60 if status_code == 429 else 120)
                        return await self.transcribe_file(blob_client, file_name, file_data)
                    if status_code == 400 and "EmptyAudioFile" in str(exc.response.content if exc.response else ""):
                        logging.warning("Bad Request: %s. Signaling empty audio file.", str(exc))
                        return self._short_call_result("empty_audio_file")
                    if status_code == 400 and "InvalidAudioFile" in str(exc.response.content if exc.response else ""):
                        logging.warning("Bad Request: %s. Signaling invalid audio file.", str(exc))
                        return {"text": "Invalid Audio File."}
                    if status_code == 400 and "Maximal audio length exceeded" in str(exc.response.content if exc.response else ""):
                        logging.warning("Bad Request: %s. Signaling too large file.", str(exc))
                        return {"text": "Audio file too big. Manual processing required."}
                    logging.critical("Unhandled HTTP error: %s.", str(exc.response.content if exc.response else exc))
                    raise exc
                except Exception as exc:
                    logging.critical("Unhandled error: %s.", str(exc))
                    raise exc

    def _parse_storage_connection_string(self, conn_str: str) -> tuple[str | None, str | None]:
        if not conn_str:
            return None, None
        parts: dict[str, str] = {}
        for segment in conn_str.split(";"):
            if not segment or "=" not in segment:
                continue
            key, value = segment.split("=", 1)
            parts[key.strip()] = value.strip()
        return parts.get("AccountName"), parts.get("AccountKey")

    def _generate_blob_sas_url(self, blob_client: BlobClient, expiry_minutes: int = 60) -> str | None:
        if not self.storage_account_name or not self.storage_account_key:
            return None
        sas_token = generate_blob_sas(
            account_name=self.storage_account_name,
            container_name=blob_client.container_name,
            blob_name=blob_client.blob_name,
            account_key=self.storage_account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes),
        )
        return f"{blob_client.url}?{sas_token}"

    def _build_speech_transcription_url(self) -> str | None:
        base = os.getenv("AI_SPEECH_URL", "").rstrip("/")
        if not base:
            return None
        api_version = os.getenv("AI_SPEECH_API_VERSION", "2025-10-15")
        return f"{base}/speechtotext/transcriptions:submit?api-version={api_version}"

    def _normalize_job_location(self, job_url: str) -> str:
        api_version = os.getenv("AI_SPEECH_API_VERSION", "2025-10-15")
        normalized = job_url.replace("transcriptions:submit", "transcriptions")
        if "api-version" not in normalized:
            separator = "&" if "?" in normalized else "?"
            normalized = f"{normalized}{separator}api-version={api_version}"
        return normalized

    def _build_batch_transcription_payload(self, file_name: str, sas_url: str, locales: list[str] = ["en-US", "es-MX"]) -> dict:
        profanity_mode = os.getenv("SPEECH_PROFANITY_MODE", "Masked")
        word_timestamps = os.getenv("SPEECH_WORD_TIMESTAMPS", "true").lower() in {"true", "1", "yes"}
        diarization_enabled = os.getenv("SPEECH_DIARIZATION", "false").lower() in {"true", "1", "yes"}
        payload: dict[str, object] = {
            "displayName": f"tayra-{Path(file_name).stem}",
            "description": "Tayra batch transcription",
            "contentUrls": [sas_url],
            "properties": {
                "diarization":{
                    "enabled": diarization_enabled,
                    "maxSpeakerCount": 10
                },
                "wordLevelTimestampsEnabled": word_timestamps,
                "profanityFilterMode": profanity_mode,
                "timeToLiveHours": 48,
                
            },
        }
        payload["locale"] = locales[0]
        if len(locales) > 1:
            payload["properties"]["languageIdentification"] = {
                "candidateLocales": list(locales),
                "mode": "Continuous",
            }
        return payload

    async def _poll_transcription_job(self, client: httpx.AsyncClient, job_url: str, headers: dict[str, str], timeout_seconds: int = 900, poll_interval: int = 5):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            response = await client.get(job_url, headers=headers)
            response.raise_for_status()
            job_data = response.json()
            status = job_data.get("status")
            if status in {"Succeeded", "Failed"}:
                return job_data
            await asyncio.sleep(poll_interval)
        logging.error("Speech batch job at %s timed out after %s seconds", job_url, timeout_seconds)
        return {"status": "Failed", "error": {"message": "timeout"}}

    async def _download_batch_transcript(self, client: httpx.AsyncClient, job_data: dict, headers: dict[str, str]) -> str | None:
        files_url = job_data.get("links", {}).get("files")
        if not files_url:
            logging.error("Speech batch job does not contain files link")
            return None

        files_response = await client.get(files_url, headers=headers)
        files_response.raise_for_status()
        files_payload = files_response.json()
        for file_info in files_payload.get("values", []):
            if file_info.get("kind", "").lower() != "transcription":
                continue
            content_url = file_info.get("links", {}).get("contentUrl") or file_info.get("contentUrl")
            if not content_url:
                continue
            transcript_response = await client.get(content_url)
            transcript_response.raise_for_status()
            transcript_payload = transcript_response.json()
            combined_phrases = transcript_payload.get("combinedRecognizedPhrases") or []
            text_segments = [phrase.get("display", "").strip() for phrase in combined_phrases if phrase.get("display")]
            if text_segments:
                return " ".join(text_segments)
        return None

    async def save_transcription(
        self,
        blob_name: str,
        transcription_text,
        transcription_metadata,
        short_reason: str | None = None,
    ):
        transcription_file_name = str(os.path.splitext(blob_name)[0]).split("/")

        specialist_name = transcription_file_name[1] if len(transcription_file_name) > 1 else "UNKNOWN"
        manager_name = transcription_file_name[0] if len(transcription_file_name) > 0 else "UNKNOWN"

        is_valid_call = "YES" if transcription_text != self.SHORT_CALL_TEXT else "NO"

        transcription = Transcription(
            id=str(uuid.uuid4()),
            filename=blob_name,
            transcription=transcription_text,
            metadata=transcription_metadata,
            is_valid_call=is_valid_call,
            failure_reason=short_reason if is_valid_call == "NO" else None,
        )

        specialist = SpecialistItem(
            id=str(uuid.uuid4()),
            name=str(specialist_name).upper(),
            transcriptions = [transcription]
        )

        manager = ManagerModel(
            id=str(uuid.uuid4()),
            name=str(manager_name[0]).upper(),
            assistants=[specialist]
        )

        async with self._get_cosmos_client() as client:
            try:
                database = client.get_database_client(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
                await database.read()
            except exceptions.CosmosResourceNotFoundError:
                await client.create_database(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
            container = database.get_container_client(os.getenv("CONTAINER_NAME", "transcriptions"))
            manager_items = container.query_items(
                query=f"SELECT * FROM c WHERE c.name = '{manager.name}'"
            )
            manager_item = [item async for item in manager_items] if manager_items else None

            if manager_item:
                manager = ManagerModel(**manager_item[0])
                specialist_found = False
                for existing_specialist in manager.assistants:
                    if existing_specialist.name == specialist.name:
                        existing_specialist.transcriptions.append(transcription)
                        specialist_found = True
                        break
                if not specialist_found:
                    manager.assistants.append(specialist)
                await container.upsert_item(manager.model_dump())
            else:
                await container.create_item(manager.model_dump())

        logging.info("Transcription saved at: %s", transcription.id)

    def _should_use_aad_auth(self) -> bool:
        flag = os.getenv("COSMOS_USE_AAD", "")
        if flag:
            return flag.lower() in {"1", "true", "yes"}
        return not bool(self.cosmos_key)

    def _get_cosmos_client(self):
        if self.use_aad_auth:
            if not self._aad_credential:
                self._aad_credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            return CosmosClient(self.cosmos_endpoint, credential=self._aad_credential)
        if not self.cosmos_key:
            raise RuntimeError("COSMOS_KEY is empty and AAD auth is disabled. Set COSMOS_USE_AAD=true or provide a key.")
        return CosmosClient(self.cosmos_endpoint, self.cosmos_key)


def _get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes"}


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        logging.warning("Invalid integer for %s=%s. Using default %s", name, value, default)
        return default


def _build_params_from_env() -> TranscriptionJobParams:
    return TranscriptionJobParams(
        origin_container=os.getenv("TRANSCRIPTION_ORIGIN_CONTAINER", "audio-files"),
        destination_container=os.getenv("TRANSCRIPTION_DESTINATION_CONTAINER", "transcripts"),
        manager_name=os.getenv("TRANSCRIPTION_MANAGER_NAME"),
        specialist_name=os.getenv("TRANSCRIPTION_SPECIALIST_NAME"),
        limit=_get_env_int("TRANSCRIPTION_LIMIT", -1),
        only_failed=_get_env_bool("TRANSCRIPTION_ONLY_FAILED", False),
        use_cache=_get_env_bool("TRANSCRIPTION_USE_CACHE", False),
        run_evaluation_flow=_get_env_bool("TRANSCRIPTION_EVAL_FLOW", True),
        semaphores=_get_env_int("TRANSCRIPTION_SEMAPHORES", 10),
        results_per_page=_get_env_int("TRANSCRIPTION_RESULTS_PER_PAGE", 50),
    )


async def main_transcribe_async() -> None:
    processor = BlobTranscriptionProcessor()
    params = _build_params_from_env()
    await processor(params)


def main_transcribe() -> None:
    asyncio.run(main_transcribe_async())


if __name__ == "__main__":
    main_transcribe()
