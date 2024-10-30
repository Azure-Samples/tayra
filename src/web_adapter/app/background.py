"""
_summary_
"""

from concurrent.futures import ProcessPoolExecutor
from app.ingest import upload_job


def run_upload_job(
    file_address: str,
    manager_name: str,
    specialist_name: str,
    destination_container: str = "audio-files"
):
    """
    Função para executar o job de upload em um subprocesso.
    """
    with ProcessPoolExecutor() as executor:
        future = executor.submit(
            upload_job,
            destination_container,
            file_address,
            manager_name,
            specialist_name
        )
        future.result()

