from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Base template used across chat-related prompts."""

    prompt: str = Field(..., description="Prompt text sent to the model.")
    history: str | None = Field(default=None, description="Serialized chat history, if any.")
    context: str | None = Field(default=None, description="Additional contextual information.")
    function_name: str | None = Field(
        default=None, description="Optional function name tied to this template."
    )


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
