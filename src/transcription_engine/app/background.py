"""
_summary_
"""

import asyncio

from app.transcribe import BlobTranscriptionProcessor
from app.schemas import TranscriptionJobParams


def run_transcription_job(parameters: TranscriptionJobParams):
    """
    Função para executar o job de upload em um subprocesso.
    """
    processor = BlobTranscriptionProcessor()
    asyncio.run(processor(parameters))
