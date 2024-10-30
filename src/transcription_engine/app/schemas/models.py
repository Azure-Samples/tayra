"""

"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Transcription(BaseModel):
    id: str
    filename: str
    transcription: str
    is_valid_call: str
    metadata: dict


class SpecialistItem(BaseModel):
    id: str
    name: str
    transcriptions: List[Transcription]
    role: Optional[str] = Field(default="Specialist", title="The role of the assistant")

    def total_transcriptions(self) -> int:
        return len(self.transcriptions)


class ManagerItem(BaseModel):
    id: str
    name: str
    assistants: List[SpecialistItem]
    role: Optional[str] = Field(default="Manager", title="The role of the manager")

    def transcriptions(self) -> int:
        return sum(
            specialist.total_transcriptions()
            for specialist in self.assistants
        )
