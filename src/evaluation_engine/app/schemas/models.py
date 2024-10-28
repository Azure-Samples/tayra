"""

"""

from typing import List, Optional
from pydantic import BaseModel, Field


class EvaluationItem(BaseModel):
    item: str
    subitem: str
    description: str
    weight: int


class Evaluation(BaseModel):
    items: List[EvaluationItem]
    total_score: int
    classification: str
    improvement_suggestion: str


class AditionalEvaluation(BaseModel):
    client: str = Field(
        default="Not Identified",
        description="""
        Name of the client, if identified in the transcription.
        """,
    )

    conversation_topic: Optional[str] = Field(
        ...,
        description="""
        The topic of the conversation, categorized as PERSONAL, QUESTION, SERVICE, or OTHER.
        """,
    )

    propensity: Optional[str] = Field(
        ...,
        description="""
        Validates whether the client is interested in following the suggestion, and what in the conversation indicates that this would be the action.
        """,
    )


class HumanEvaluation(BaseModel):
    evaluator: str
    classification: str
    items: List[EvaluationItem]


class UnitaryEvaluation(BaseModel):
    tipo: str
    prompt: str
    transcription: str


class TranscriptionImprovementRequest(BaseModel):
    transcription_data: str


class SubItem(BaseModel):
    sub_item: str = Field(default=None, description="Evaluated sub item")
    description: str = Field(default=None, description="Description of the evaluated sub item")
    score: int = Field(default=None, description="Score assigned to the sub item")
    justification: str = Field(default=None, description="Justification for the assigned score")


class Item(BaseModel):
    item: str = Field(..., description="Name of the evaluated item")
    description: str = Field(..., description="Description of the evaluated item")
    score: int = Field(..., description="Score assigned to the item")
    justification: str = Field(..., description="Justification for the assigned score")
    sub_item: List[SubItem] = Field(..., description="List of evaluated sub items")
