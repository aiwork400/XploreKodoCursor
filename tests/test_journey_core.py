from __future__ import annotations

import pytest

from mvp_v1.models import CandidateProfile, CandidateTrack
from mvp_v1.legal.visa_compliance_agent import VisaComplianceAgent
from mvp_v1.services import DocumentVault


@pytest.fixture
def document_vault() -> DocumentVault:
    return DocumentVault()


def test_student_remains_incomplete_until_all_documents_and_requirements(document_vault: DocumentVault) -> None:
    candidate = CandidateProfile(
        candidate_id="stu-001",
        full_name="Student One",
        track=CandidateTrack.STUDENT,
    )

    # Initially: no docs, no flags
    compliant, next_status = VisaComplianceAgent.evaluate_candidate(candidate)
    assert compliant is False
    assert next_status == "Incomplete"

    # Upload only passport and transcript
    document_vault.store_document(candidate.candidate_id, "passport", "/secure/passports/stu-001.pdf")
    document_vault.store_document(candidate.candidate_id, "transcript", "/secure/transcripts/stu-001.pdf")
    assert document_vault.has_all_core_documents(candidate.candidate_id) is False

    # Even after setting study certificate, still missing financial sponsor docs
    candidate.has_150_hour_study_certificate = True
    compliant, next_status = VisaComplianceAgent.evaluate_candidate(candidate)
    assert compliant is False
    assert next_status == "Incomplete"

    # Upload COE and set sponsor docs
    document_vault.store_document(candidate.candidate_id, "coe", "/secure/coe/stu-001.pdf")
    candidate.has_financial_sponsor_docs = True

    # Now all SOW-mandated fields are satisfied
    assert document_vault.has_all_core_documents(candidate.candidate_id) is True
    compliant, next_status = VisaComplianceAgent.evaluate_candidate(candidate)
    assert compliant is True
    assert next_status == "ReadyForSubmission"


def test_jobseeker_remains_incomplete_until_all_documents_and_requirements(document_vault: DocumentVault) -> None:
    candidate = CandidateProfile(
        candidate_id="job-001",
        full_name="Jobseeker One",
        track=CandidateTrack.JOBSEEKER,
    )

    # Initially: no docs, no JLPT/Kaigo
    compliant, next_status = VisaComplianceAgent.evaluate_candidate(candidate)
    assert compliant is False
    assert next_status == "Incomplete"

    # Upload some docs but miss certificates
    document_vault.store_document(candidate.candidate_id, "passport", "/secure/passports/job-001.pdf")
    document_vault.store_document(candidate.candidate_id, "coe", "/secure/coe/job-001.pdf")
    document_vault.store_document(candidate.candidate_id, "transcript", "/secure/transcripts/job-001.pdf")
    assert document_vault.has_all_core_documents(candidate.candidate_id) is True

    compliant, next_status = VisaComplianceAgent.evaluate_candidate(candidate)
    assert compliant is False
    assert next_status == "Incomplete"

    # Provide JLPT but no Kaigo
    candidate.has_jlpt_n4_or_n5 = True
    compliant, next_status = VisaComplianceAgent.evaluate_candidate(candidate)
    assert compliant is False
    assert next_status == "Incomplete"

    # Finally, provide Kaigo Skills Test results
    candidate.has_kaigo_skills_test = True
    compliant, next_status = VisaComplianceAgent.evaluate_candidate(candidate)
    assert compliant is True
    assert next_status == "ReadyForSubmission"


