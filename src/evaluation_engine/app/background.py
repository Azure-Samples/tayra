"""
_summary_
"""

import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor

from app.schemas import EvaluationEndpoint, TranscriptionInterface, Transcription
from app.evaluate import EvaluateTranscription


logger = logging.getLogger(__name__)


def evaluation_job(
        transcription_interface: TranscriptionInterface,
        theme: str,
        criteria: List
    ):
    transcription = Transcription(
        id=transcription_interface.id,
        transcription=transcription_interface.transcription,
        criteria=criteria,
        theme=theme
    )
    evaluation_flow = EvaluateTranscription()
    return evaluation_flow(transcription)


def run_evaluation_job(parameters: EvaluationEndpoint) -> None:

    with ThreadPoolExecutor() as executor:

        tasks = [
            executor.submit(
                evaluation_job,
                transcription,
                parameters.criteria,
                parameters.theme
            )
            for transcription in parameters.transcriptions
        ]

        response = [task.result() for task in tasks]
    logger.info(response)
