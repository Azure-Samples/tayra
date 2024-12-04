import asyncio
import io
import json
import logging
import os
import sys
import time
import uuid
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import List

import httpx
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions
from azure.storage.blob.aio import BlobClient, BlobServiceClient
from dotenv import find_dotenv, load_dotenv

sys.path.append(os.getcwd())

from app.schemas import TranscriptionJobParams, Transcription, SpecialistItem, ManagerModel

load_dotenv(find_dotenv())
logging.getLogger('azure').setLevel(logging.WARNING)
DEFAULT_CREDENTIAL = DefaultAzureCredential()

class BlobTranscriptionProcessor:
    BATCH_SIZE = 50

    def __init__(self):
        self.storage_account_name = os.getenv("STORAGE_ACCOUNT_NAME", "")
        self.ai_speech_key = os.getenv("AI_SPEECH_KEY", "")
        self.cosmos_endpoint = os.getenv("COSMOS_ENDPOINT", "")
        self.cosmos_key = os.getenv("COSMOS_KEY", "")
        self.failed_files = set()

    async def __call__(self, params: TranscriptionJobParams):
        """Run the entire processing logic using the provided parameters."""
        listener = await self.init_logger()
        try:
            await self.process_blob_storage(params)
        finally:
            listener.stop()

    async def init_logger(self):
        log = logging.getLogger()
        que = Queue()
        queue_handler = QueueHandler(que)
        log.addHandler(queue_handler)
        log.setLevel(logging.INFO)
        listener = QueueListener(que, logging.StreamHandler(stream=sys.stdout))
        listener.start()
        logging.debug('Logger has started')
        return listener

    async def get_failed_transcriptions(self):
        async with CosmosClient(self.cosmos_endpoint, credential=DEFAULT_CREDENTIAL) as client:
            try:
                database = client.get_database_client(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
                await database.read()
            except exceptions.CosmosResourceNotFoundError:
                await client.create_database(os.getenv("COSMOS_DB_TRANSCRIPTION", "transcription_job"))
            container = database.get_container_client(os.getenv("CONTAINER_NAME", "transcriptions"))
            failed_items = container.query_items(
                query="SELECT * FROM c WHERE c.is_valid_call != 'SIM'",
            )

            self.failed_files = {
                f"{'/'.join(str(os.path.splitext(item.get('filename', ''))[0]).split('/')[-3:])}"
                async for item in failed_items
            }

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
        async with BlobServiceClient(account_url=f"https://{self.storage_account_name}.blob.core.windows.net", 
                                     credential=DEFAULT_CREDENTIAL) as blob_service_client:
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
        start_overall = time.time()
        logging.info("Starting job on %s", start_overall)

        await self.get_failed_transcriptions()
        checked_transcriptions_cache = {}
        prefix = self._set_prefix(params)

        results_per_page = params.results_per_page
        if not results_per_page:
            results_per_page = self.BATCH_SIZE

        transcription_metadata, counter = await self._process_batch(prefix, checked_transcriptions_cache, results_per_page, params)

        end_overall = time.time()
        logging.info("Job finished on %s", end_overall)
        overall_duration = end_overall - start_overall

        logging.info(
            "Processed %s blobs in %s seconds.\n",
            counter,
            overall_duration,
        )

        metadata = {
            "transcription_duration": overall_duration,
            "processed_files": counter,
            "transcriptions": transcription_metadata,
        }

        logging.info("Metadata: %s", transcription_metadata)

        metadata_json = json.dumps(metadata, ensure_ascii=True)
        output_file = f"metadata-{str(time.time())}.json"

        async with BlobServiceClient(account_url=f"https://{self.storage_account_name}.blob.core.windows.net", 
                                     credential=DEFAULT_CREDENTIAL) as blob_service_client:
            metadata_blob_client = blob_service_client.get_blob_client(
            container=params.origin_container, blob=output_file
            )

            await metadata_blob_client.upload_blob(metadata_json, overwrite=True)
        logging.info("Metadata written to file: %s", output_file)
        logging.info("Finished uploading to blob: %s", output_file)
        print("Tarefas: ", len(transcription_metadata))

    async def is_blob_valid(
        self,
        blob,
        checked_transcriptions_cache: dict,
        blob_service_client: BlobServiceClient,
        transcription_params: TranscriptionJobParams
    ) -> bool:
        condition_file = any(blob.name.endswith(ext) for ext in ["mp3", "wav"])
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
            logging.warning("Skipping blob %s since it is not a failed file.\n", blob.name)
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

            transcription_text = transcription_result.get("text", "Unable to process :/")
            blob_properties = await blob_client.get_blob_properties()
            transcription_metadata = {
                "file_name": str(blob_name).lower().replace(" ", "_"),
                "file_size": blob_properties.size,
                "transcription_duration": time.time() - start_transcription,
            }

            start_saving = time.time()
            await self.save_transcription(
                blob_name,
                transcription_text,
                transcription_metadata,
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
        file_content = (file_name, file_data.read())
        url = os.getenv("AI_SPEECH_URL", "")
        payload = {"definition": "{\"locales\": [\"pt-BR\"], \"profanityFilterMode\": \"None\", \"channels\":[0,1]}"}
        files = [("audio", file_content)]
        headers = {"Ocp-Apim-Subscription-Key": self.ai_speech_key, "Accept": "application/json"}

        async with asyncio.Semaphore(sem):
            async with httpx.AsyncClient(timeout=None) as client:
                try:
                    response = await client.post(url, headers=headers, data=payload, files=files)
                    response.raise_for_status()
                    result = response.json()["combinedPhrases"]
                    if not result:
                        return {"text": "Call too short or not answered."}
                    if result[0].get("text") == "":
                        return {"text": "Call too short or not answered."}
                except httpx.NetworkError as exc:
                    logging.error("Network Error: %s. Trying Again.", str(exc))
                    await asyncio.sleep(0.5)
                    return await self.transcribe_file(blob_client, file_name, file_data)
                except httpx.HTTPStatusError as exc:
                    if response.status_code in [503, 429, 500, 408, 499]:
                        logging.error("Server error %s: %s. Trying Again.", response.status_code, str(exc))
                        await asyncio.sleep(60 if response.status_code == 429 else 120)
                        return await self.transcribe_file(blob_client, file_name, file_data)
                    if response.status_code == 400 and "EmptyAudioFile" in str(response.content):
                        logging.warning("Bad Request: %s. Signaling empty audio file.", str(exc))
                        return {"text": "Call too short or not answered."}
                    if response.status_code == 400 and "InvalidAudioFile" in str(response.content):
                        logging.warning("Bad Request: %s. Signaling invalid audio file.", str(exc))
                        return {"text": "Invalid Audio File."}
                    if response.status_code == 400 and "Maximal audio length exceeded" in str(response.content):
                        logging.warning("Bad Request: %s. Signaling too large file.", str(exc))
                        return {"text": "Audio file too big. Manual processing required."}
                    logging.critical("Unhandled HTTP error: %s.", str(exc.response.content))
                    raise exc
                except Exception as exc:
                    logging.critical("Unhandled error: %s.", str(exc))
                    raise exc
                else:
                    return result[0]

    async def save_transcription(
        self,
        blob_name: str,
        transcription_text,
        transcription_metadata,
    ):
        transcription_file_name = str(os.path.splitext(blob_name)[0]).split("/")

        transcription = Transcription(
            id=str(uuid.uuid4()),
            filename=blob_name,
            transcription=transcription_text,
            metadata=transcription_metadata,
            is_valid_call="YES" if transcription_text != "Call too short or not answered." else "NO"
        )

        specialist = SpecialistItem(
            id=str(uuid.uuid4()),
            name=str(transcription_file_name[1]).upper(),
            transcriptions = [transcription]
        )

        manager = ManagerModel(
            id=str(uuid.uuid4()),
            name=str(transcription_file_name[0]).upper(),
            assistants=[specialist]
        )

        async with CosmosClient(self.cosmos_endpoint, credential=DEFAULT_CREDENTIAL) as client:
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
