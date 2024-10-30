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


class TranscriptionJobParams(BaseModel):
    """
    Represents the parameters for a transcription job.
    Attributes:
        origin_container (str, optional): The origin container for audio files. Defaults to "audio-files".
        destination_container (str, optional): The destination container for transcripts. Defaults to "transcripts".
        manager_name (str, optional): The name of the manager. Defaults to None.
        specialist_name (str, optional): The name of the specialist. Defaults to None.
        limit (int, optional): The limit for the number of transcription jobs. Defaults to -1.
        only_failed (bool, optional): Flag indicating whether to retrieve only failed transcription jobs. Defaults to True.
        use_cache (bool, optional): Flag indicating whether to use cache. Defaults to False.
    """

    origin_container: str
    destination_container: str
    manager_name: Optional[str] = Field(default=None)
    specialist_name: Optional[str] = Field(default=None)
    limit: Optional[int] = Field(default=-1)
    only_failed: Optional[bool] = Field(default=True)
    use_cache: Optional[bool] = Field(default=False)
    run_evaluation_flow: Optional[bool] = Field(default=True)
    semaphores: Optional[int] = Field(default=10)
    results_per_page: Optional[int] = Field(default=50)
