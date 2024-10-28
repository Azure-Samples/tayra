"""
_summary_
"""

import asyncio

from app.transcribe import BlobTranscriptionProcessor
from app.schemas import TranscriptionJobParams


def run_evaluation_job(parameters: TranscriptionJobParams):
    """
    Função para executar o job de avaliação em um subprocesso.
    """
    processor = BlobTranscriptionProcessor()
    asyncio.run(processor(parameters))


def run_transcription_job(parameters: TranscriptionJobParams):
    """
    Função para executar o job de upload em um subprocesso.
    """
    processor = BlobTranscriptionProcessor()
    asyncio.run(processor(parameters))
    if parameters.run_evaluation_flow:
        run_evaluation_job(parameters)

