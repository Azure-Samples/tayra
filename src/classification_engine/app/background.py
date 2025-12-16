"""Background helpers for classification FastAPI entry points."""

import asyncio

from .classify import ClassificationPipeline
from .schemas import ClassificationJobParams


def run_classification_job(params: ClassificationJobParams) -> None:
    """Execute the classification pipeline within a fresh event loop."""

    pipeline = ClassificationPipeline(
        manager_name=params.manager_name,
        specialist_name=params.specialist_name,
        limit=params.limit,
        skip_already_classified=params.skip_already_classified,
        only_valid_calls=params.only_valid_calls,
    )
    asyncio.run(pipeline.run())
