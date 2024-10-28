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

from typing import List

from pydantic import BaseModel


class EvaluationItem(BaseModel):
    item: str
    sub_item: str
    descricao: str
    peso: int


class Evaluation(BaseModel):
    items: List[EvaluationItem]
    pontuacao_total: int
    classificao: str
    sugestoes_melhoria: str


class EvaluationModel(BaseModel):
    id: str
    manager: str
    assistant: str
    filename: str
    transcription: str
    evaluation: Evaluation
    is_valid_call: str
    _rid: str
    _self: str
    _etag: str
    _attachments: str
    _ts: int


database_schema = {
    "Evaluation Table": EvaluationModel.model_json_schema()
}
