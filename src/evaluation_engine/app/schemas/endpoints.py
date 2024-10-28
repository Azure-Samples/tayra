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

from pydantic import BaseModel


class SpecialistInterface(BaseModel):
    """
    Represents a specialist interface.
    Attributes:
        name (str): The name of the specialist.
        role (str): The role of the specialist.
        transcriptions (int): The number of transcriptions performed by the specialist.
        performance (int): The performance rating of the specialist.
    """

    name: str
    role: str


class ManagerInterface(BaseModel):
    """
    A Pydantic BaseModel representing a manager interface.
    Attributes:
        name (str): The name of the manager.
        role (str): The role of the manager.
        transcriptions (int): The number of transcriptions performed by the manager.
        performance (int): The performance rating of the manager.
        specialists (List[SpecialistInterface]): A list of specialist interfaces associated with the manager.
    """

    name: str
    role: str
