from typing import Any, Dict, List

from aistudio_requests.schemas import PromptTemplate


class QueryTemplate(PromptTemplate):
    query_type: str
    programming_language: str
    db_params: Dict[str, str | List[str]]


class ComplexQueryTemplate(QueryTemplate):
    db_mapping: Dict[str, str | Dict[str, Any]]


class TableToNaturalTemplate(PromptTemplate):
    data: str
    original_prompt: str


class SingleEvaluationTemplate(PromptTemplate):
    tipo: str
    transcription: str


class TranscriptionImprovementTemplate(PromptTemplate):
    transcription: str
