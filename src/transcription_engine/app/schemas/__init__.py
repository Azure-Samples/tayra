"""
A package that holds response schemas and models.
"""

__all__ = [
    "BodyMessage",
    "RESPONSES",
    "Transcription",
    "TranscriptionJobParams",
    "ManagerItem",
    "SpecialistItem",
    "UploadJobParams",
    "ManagerModel"
]
__author__ = "LATAM AI GBB TEAM"


from .database import ManagerModel
from .responses import RESPONSES, BodyMessage
from .jobs import TranscriptionJobParams, UploadJobParams
from .models import ManagerItem, SpecialistItem, Transcription
