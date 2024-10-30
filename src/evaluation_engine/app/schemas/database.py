"""
This module contains the schema definitions for the endpoints used in the application.
Classes:
- TranscriptionJobParams: Represents the parameters for a transcription job.
- SpecialistInterface: Represents the interface for a specialist.
- ManagerInterface: Represents the interface for a manager.
Attributes:
- origin_container: The optional origin container for the transcription job. Defaults to "audio-files".
- destination_container: The optional destination container for the transcription job. Defaults to "transcripts".
- manager_name: The optional name of the manager.
- specialist_name: The optional name of the specialist.
- limit: The optional limit for the transcription job. Defaults to -1.
- only_failed: The optional flag indicating whether to include only failed transcriptions. Defaults to True.
- use_cache: The optional flag indicating whether to use cache. Defaults to False.
Methods:
- None
"""

from typing import List, Optional
from pydantic import BaseModel


class EvaluationItem(BaseModel):
    item: str
    sub_item: str
    description: str
    score: int


class Evaluation(BaseModel):
    items: List[EvaluationItem]
    total_score: Optional[int]
    classification: Optional[str]
    improvement_suggestions: Optional[str]


class EvaluationModel(BaseModel):
    id: str
    transcription_id: str
    transcription: str
    evaluation: Evaluation


database_schema = {
    "Evaluation Table": EvaluationModel.model_json_schema()
}
