"""
This script processes and uploads files to a document engine using Azure Blob Storage.
It can handle individual files, folders, or zip archives containing multiple files.

Functions:
    process_file(file_address: str) -> str
        Processes a single file and uploads its content to the document engine.

    process_multiple_files(file_address: str) -> str
        Processes multiple files in a folder concurrently.

    upload_job(file_address: str) -> str
        Determines the type of file address (file, folder, or zip) and processes accordingly.

Usage:
    Set the environment variables BLOB_CONNECTION_STRING, BLOB_STORAGE_CONTAINER, and BLOB_ROOT_FOLDER
    to the appropriate values for Azure Blob Storage.

    Call the main() function to start the upload job.
"""

import asyncio
import io
import logging
import os
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed

from azure.storage.blob.aio import BlobServiceClient

# Load environment variables
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

BLOB_CONN = os.getenv("BLOB_CONNECTION_STRING", "")
BLOB_CONTAINER = os.getenv("BLOB_STORAGE_CONTAINER", "")

logger = logging.getLogger("azure")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


async def get_blob_properties(blob_client):
    try:
        blob_properties = await blob_client.get_blob_properties()
        return blob_properties
    except Exception as exc:
        logging.warning("Failed to get blob properties: %s", str(exc))
        return None


async def upload_file_to_blob(
    container_name: str,
    file_name: str,
    file_content: io.BytesIO,
    manager_name: str,
    specialist_name: str,
) -> None:
    """
    Upload a file to Azure Blob Storage.
    """
    try:
        file_name = "".join(c for c in file_name if c.isalnum() or c == ".")
        async with BlobServiceClient.from_connection_string(BLOB_CONN) as blob_service_client:
            blob_path = f"{manager_name}/{specialist_name}/{file_name}"
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_path
            )

            await blob_client.upload_blob(file_content.getvalue())
            logger.info("Successfully uploaded file: %s", blob_path)

    except Exception as e:
        logger.error("Error occurred while uploading to Azure Blob Storage: %s", str(e))
        raise e


def process_file(
        container_name: str,
        file_address: str,
        manager: str,
        specialist: str
    ) -> str:
    """
    Process a file and upload its content to a document engine.

    Args:
        file_address (str): The address of the file to be processed.

    Returns:
        str: A message indicating the success or failure of the file processing.

    Raises:
        Exception: If there is an error during the file processing.
    """

    logger.info("Routine to process files.")
    logger.info("File Address: %s", file_address)
    start_time = time.time()

    try:
        with open(file_address, "rb") as file_content:
            buffer = io.BytesIO(file_content.read())

        file_name = os.path.basename(file_address)
        specialist_name = specialist
        manager_name = manager

        asyncio.run(
            upload_file_to_blob(
                container_name=container_name,
                manager_name=manager_name,
                specialist_name=specialist_name,
                file_content=buffer,
                file_name=file_name,
            )
        )

        end_time = time.time()
        duration = end_time - start_time
        logger.info("Execution time for process_file: %s seconds", duration)
        os.remove(file_address)
        return f"File {file_address} processed successfully."
    except Exception as e:
        logger.error("Error processing file %s: %s", file_address, str(e))
        end_time = time.time()
        duration = end_time - start_time
        logger.info("Execution time for process_file: %s seconds", duration)
        return f"Error processing file {file_address}: {str(e)}"


def process_multiple_files(
        container_name: str,
        file_address: str,
        manager: str,
        specialist: str
    ) -> str:
    """
    Process multiple files in a folder concurrently.

    Args:
        file_address (str): The address of the folder containing files to be processed.

    Returns:
        str: A message indicating the success or failure of the file processing.
    """

    file_names = []
    for root, dirs, files in os.walk(file_address):
        for file in files:
            file_names.append(os.path.join(root, file))

    results = []
    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(process_file, container_name, file_name, manager, specialist): file_name
            for file_name in file_names
        }
        for future in as_completed(futures):
            file_name = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error("Error processing file %s: %s", file_name, str(e))
                results.append(f"Error processing file {file_name}: {str(e)}")

    return "\n".join(results)


def upload_job(container_name: str, file_address: str, manager: str, specialist: str) -> str:
    """
    Uploads a file or a folder to the ingestion engine for processing.

    Args:
        file_address (str): The address of the file or folder to be uploaded.

    Returns:
        str: The result of the upload process.

    Raises:
        AttributeError: If the file address is not a valid folder, file, or zip folder.
    """

    logger.info("Routine to upload files.")
    logger.info("File Address: %s", file_address)

    if os.path.isdir(file_address):
        logger.info("File Address is a folder.")
        upload_type = "folder"
    elif os.path.isfile(file_address):
        if file_address.endswith(".zip"):
            upload_type = "zip"
            logger.info("File Address is a zip folder.")
        else:
            upload_type = "file"
            logger.info("File Address is a file.")
    else:
        logger.error("File Address is not a valid folder, file, or zip folder.")
        raise AttributeError("File Address is not a valid folder, file, or zip folder.")

    try:
        match upload_type:
            case "file":
                return process_file(
                    container_name=container_name,
                    file_address=file_address,
                    manager=manager,
                    specialist=specialist
                )
            case "folder":
                return process_multiple_files(
                    container_name,
                    file_address,
                    manager=manager,
                    specialist=specialist
                )
            case "zip":
                with zipfile.ZipFile(file_address, "r") as zip_ref:
                    zip_ref.extractall("/tmp/extracted_files")
                return process_multiple_files(
                    container_name,
                    "/tmp/extracted_files",
                    manager=manager,
                    specialist=specialist
                )
            case _:
                return "Invalid upload type."
    except Exception as e:
        logger.error("Error during upload: %s", str(e))
        return f"Error during upload: {str(e)}"
