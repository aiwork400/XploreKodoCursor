from __future__ import annotations

from typing import Tuple

from mvp_v1.models import CandidateProfile, CandidateTrack


class VisaComplianceAgent:
    """
    VisaComplianceAgent

    Evaluates whether a candidate has satisfied the SOW-mandated document
    requirements for their track (Student or Jobseeker).
    """

    @staticmethod
    def is_student_compliant(candidate: CandidateProfile) -> bool:
        """
        Student Path:
        - 150-hour study certificate
        - Financial Sponsor documentation
        """
        if candidate.track != CandidateTrack.STUDENT:
            return False

        return bool(
            candidate.has_150_hour_study_certificate
            and candidate.has_financial_sponsor_docs
        )

    @staticmethod
    def is_jobseeker_compliant(candidate: CandidateProfile) -> bool:
        """
        Jobseeker Path (Japan-focused for now):
        - JLPT N4/N5 certificate
        - Kaigo Skills Test results
        """
        if candidate.track != CandidateTrack.JOBSEEKER:
            return False

        return bool(candidate.has_jlpt_n4_or_n5 and candidate.has_kaigo_skills_test)

    @classmethod
    def evaluate_candidate(cls, candidate: CandidateProfile) -> Tuple[bool, str]:
        """
        Evaluate a candidate and return:
        - is_compliant: bool
        - next_status: str ("Incomplete" or "ReadyForSubmission")
        """
        if candidate.track == CandidateTrack.STUDENT:
            compliant = cls.is_student_compliant(candidate)
        elif candidate.track == CandidateTrack.JOBSEEKER:
            compliant = cls.is_jobseeker_compliant(candidate)
        else:
            compliant = False

        next_status = "ReadyForSubmission" if compliant else "Incomplete"
        return compliant, next_status


