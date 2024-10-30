from typing import Dict, List, Optional, TypedDict


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
        "sub_criteria": Optional[List[Dict]]
    }
)


Transcription = TypedDict(
    "Transcription",
    {
        "id": str,
        "theme": str,
        "transcription": str,
        "criteria": List[Criteria]
    }
)
