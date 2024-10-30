"""
_summary_
"""

from typing import List
from concurrent.futures import ThreadPoolExecutor
from promptflow.core import AzureOpenAIModelConfiguration

from app.schemas import EvaluationEndpoint, TranscriptionInterface, Transcription
from app.evaluate import EvaluateTranscription


def evaluation_job(
        transcription_interface: TranscriptionInterface,
        theme: str,
        criteria: List,
        model_config: AzureOpenAIModelConfiguration
    ):
    transcription = Transcription(
        id=transcription_interface.id,
        transcription=transcription_interface.transcription,
        criteria=criteria,
        theme=theme
    )
    evaluation_flow = EvaluateTranscription(model_config=model_config)
    return evaluation_flow(transcription)


def run_evaluation_job(
    parameters: EvaluationEndpoint,
    model_config: AzureOpenAIModelConfiguration
) -> List:

    with ThreadPoolExecutor() as executor:

        tasks = [
            executor.submit(
                evaluation_job,
                transcription,
                parameters.criteria,
                parameters.theme,
                model_config
            )
            for transcription in parameters.transcriptions
        ]

        response = [task.result() for task in tasks]
        
    return response
