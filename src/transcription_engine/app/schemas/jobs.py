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
from pydantic import BaseModel, Field, ValidationInfo, field_validator


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

    destination_container: Optional[str] = Field(default="audio-files")
    run_transcription: Optional[bool] = Field(default=True)
    run_evaluation_flow: Optional[bool] = Field(default=True)

    @field_validator("run_evaluation_flow")
    def check_evaluation_flow_dependency(cls, value, info: ValidationInfo):  # pylint: disable=no-self-argument
        """
        Validates that the `run_evaluation_flow` attribute can only be set to True if `run_transcription` is also True.

        Args:
            value (bool): The value of the `run_evaluation_flow` attribute being validated.
            info (ValidationInfo): The object containing validation context, including other field values.

        Returns:
            bool: The validated value of `run_evaluation_flow`.

        Raises:
            ValueError: If `run_evaluation_flow` is set to True while `run_transcription` is False.
        """
        run_transcription = info.data.get("run_transcription", True)
        if value and not run_transcription:
            raise ValueError(
                "`run_evaluation_flow` can only be True if `run_transcription` is also True."
            )
        return value


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
