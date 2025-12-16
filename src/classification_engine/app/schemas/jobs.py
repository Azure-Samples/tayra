"""Pydantic payloads for kicking off classification jobs."""

from typing import Optional

from pydantic import BaseModel, Field


class ClassificationJobParams(BaseModel):
    """Filtering knobs consumed by the classification pipeline."""

    manager_name: Optional[str] = Field(default=None, description="Filter by manager name.")
    specialist_name: Optional[str] = Field(
        default=None, description="Filter by specialist nested under a manager."
    )
    limit: Optional[int] = Field(
        default=-1, description="Upper bound for number of transcriptions to classify."
    )
    skip_already_classified: bool = Field(
        default=True,
        description="When true, documents with classification metadata are skipped.",
    )
    only_valid_calls: bool = Field(
        default=True,
        description="Skip transcripts whose is_valid_call flag is not YES.",
    )
