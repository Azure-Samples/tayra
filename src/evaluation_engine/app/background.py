"""
_summary_
"""

import asyncio
from promptflow.core import AzureOpenAIModelConfiguration

from app.schemas import EvaluationEndpoint
from app.evaluate import EvaluateTranscription


def run_evaluation_job(
        parameters: EvaluationEndpoint,
        model_config: AzureOpenAIModelConfiguration
    ):
    evaluation_flow = EvaluateTranscription(model_config=model_config, job_config=parameters.job)
    response = asyncio.run(evaluation_flow(parameters.transcription.model_dumps()))
    return response
