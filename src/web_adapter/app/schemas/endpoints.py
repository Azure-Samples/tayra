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

from typing import Optional
from pydantic import BaseModel, Field


class UploadJobParams(BaseModel):
    """
    Represents the parameters for an upload job, which may include transcription and evaluation flows.\n

    **Attributes**:\n
        - destination_container (str, optional): The destination container for audio files. Defaults to "audio-files".
        - run_transcription (bool, optional): Flag indicating whether to run the transcription process. Defaults to True.
        - run_evaluation_flow (bool, optional): Flag indicating whether to run the evaluation flow.
            This can only be set to True if `run_transcription` is also True. Defaults to True.

    **Raises**:\n
        ValueError: If `run_evaluation_flow` is set to True while `run_transcription` is False.
    """

    manager_name: str
    specialist_name: str
    destination_container: Optional[str] = Field(default="audio-files")
