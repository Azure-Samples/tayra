from typing import Dict, List, TypedDict
from pydantic import BaseModel


TranscriptionEnhancement = TypedDict(
    "TranscriptionEnhancement",
    {
        "transcription": str
    }
)


Criteria = TypedDict(
    "Criteria",
    {
        "topic": str,
        "business_rules": List[str],
        "sub_criteria": List[Dict]
    }
)


Transcription = TypedDict(
    "Transcription",
    {
        "theme": str,
        "transcription": str,
        "criteria": List[Criteria]
    }
)


class EvaluationJob(BaseModel):
    destination_container: str
    theme: str
    business_rules: List[str]
    criteria: List[Criteria]
