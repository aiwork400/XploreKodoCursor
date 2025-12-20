from __future__ import annotations

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class CandidateTrack(str, Enum):
    STUDENT = "student"
    JOBSEEKER = "jobseeker"


class CandidateProfile(BaseModel):
    """
    Core candidate representation for the Journey Core Engine.

    Supports two primary tracks:
    - Students
    - Jobseekers
    """

    candidate_id: str = Field(..., description="Stable identifier for the candidate.")
    full_name: str = Field(..., description="Full legal name as per passport.")
    track: CandidateTrack = Field(..., description="Candidate track: student or jobseeker.")

    # Shared document flags / paths
    passport_path: Optional[str] = Field(
        default=None,
        description="Secure path reference to the candidate's passport document.",
    )
    coe_path: Optional[str] = Field(
        default=None,
        description="Secure path reference to Certificate of Eligibility (COE), if applicable.",
    )
    transcripts_paths: List[str] = Field(
        default_factory=list,
        description="List of secure paths to educational transcripts.",
    )

    # Student-specific requirements
    has_150_hour_study_certificate: bool = Field(
        default=False,
        description="Whether the candidate has provided a 150-hour study certificate.",
    )
    has_financial_sponsor_docs: bool = Field(
        default=False,
        description="Whether financial sponsor documentation has been provided.",
    )

    # Jobseeker-specific requirements (Japan corridor focus)
    has_jlpt_n4_or_n5: bool = Field(
        default=False,
        description="Whether JLPT N4/N5 certificate has been provided.",
    )
    has_kaigo_skills_test: bool = Field(
        default=False,
        description="Whether Kaigo Skills Test result has been provided.",
    )

    status: str = Field(
        default="Incomplete",
        description="Lifecycle status of the candidate in the journey core engine.",
    )


