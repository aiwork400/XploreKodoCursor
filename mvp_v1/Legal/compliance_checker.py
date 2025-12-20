"""
Auto-Compliance Checker Service.

Queries PostgreSQL database for candidate's full profile and automatically
sets travel_ready and status based on compliance rules.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.db_manager import Candidate, CurriculumProgress, Payment, SessionLocal


class ComplianceChecker:
    """
    Auto-compliance checker that evaluates candidates against SOW requirements.

    Rules:
    - Student: 150-hour cert AND Financial Docs AND N5 Progress == 100% AND Fee Paid
    - Jobseeker: JLPT N4 AND Kaigo Test AND Fee Paid
    """

    @staticmethod
    def check_candidate_compliance(candidate_id: str, db: Session) -> tuple[bool, str]:
        """
        Check if candidate meets all compliance requirements.

        Returns:
            (is_compliant: bool, message: str)
        """
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not candidate:
            return False, f"Candidate {candidate_id} not found."

        curriculum = db.query(CurriculumProgress).filter(
            CurriculumProgress.candidate_id == candidate_id
        ).first()

        # Check if fee is paid
        successful_payment = db.query(Payment).filter(
            Payment.candidate_id == candidate_id,
            Payment.status == "success"
        ).first()

        if not successful_payment:
            return False, "Fee payment not completed."

        if candidate.track == "student":
            return ComplianceChecker._check_student_compliance(candidate, curriculum)
        elif candidate.track == "jobseeker":
            return ComplianceChecker._check_jobseeker_compliance(candidate, curriculum)
        else:
            return False, f"Unknown track: {candidate.track}"

    @staticmethod
    def _check_student_compliance(candidate: Candidate, curriculum: CurriculumProgress | None) -> tuple[bool, str]:
        """Check student compliance: 150-hour cert AND Financial Docs AND N5 Progress == 100% AND Fee Paid."""
        if not candidate.has_150_hour_study_certificate:
            return False, "Missing 150-hour study certificate."

        if not candidate.has_financial_sponsor_docs:
            return False, "Missing financial sponsor documentation."

        if not curriculum:
            return False, "Curriculum progress not initialized."

        # Check N5 progress is 100%
        n5_progress = (curriculum.jlpt_n5_units_completed / curriculum.jlpt_n5_total_units * 100) if curriculum.jlpt_n5_total_units > 0 else 0
        if n5_progress < 100:
            return False, f"JLPT N5 progress incomplete: {n5_progress:.1f}% (required: 100%)"

        return True, "Student compliance: All requirements met."

    @staticmethod
    def _check_jobseeker_compliance(candidate: Candidate, curriculum: CurriculumProgress | None) -> tuple[bool, str]:
        """Check jobseeker compliance: JLPT N4 AND Kaigo Test AND Fee Paid."""
        if not candidate.has_jlpt_n4_or_n5:
            return False, "Missing JLPT N4/N5 certificate."

        if not candidate.has_kaigo_skills_test:
            return False, "Missing Kaigo Skills Test result."

        # Additional check: Verify Kaigo modules are completed
        if curriculum:
            kaigo_basics_complete = (
                curriculum.kaigo_basics_lessons_completed >= curriculum.kaigo_basics_total_lessons
            )
            communication_complete = (
                curriculum.communication_skills_lessons_completed >= curriculum.communication_skills_total_lessons
            )
            physical_care_complete = (
                curriculum.physical_care_lessons_completed >= curriculum.physical_care_total_lessons
            )

            if not (kaigo_basics_complete and communication_complete and physical_care_complete):
                return False, "Kaigo vocational modules incomplete."

        return True, "Jobseeker compliance: All requirements met."

    @staticmethod
    def auto_update_compliance(candidate_id: str) -> str:
        """
        Auto-check compliance and update travel_ready and status if compliant.

        Returns status message.
        """
        db: Session = SessionLocal()
        try:
            candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
            if not candidate:
                return f"Candidate {candidate_id} not found."

            is_compliant, message = ComplianceChecker.check_candidate_compliance(candidate_id, db)

            if is_compliant:
                candidate.travel_ready = True
                candidate.status = "ReadyForSubmission"
                db.commit()
                
                # Trigger notification (MessengerAgent will handle this)
                notification_note = "\n📧 Notification triggered: Candidate will be notified via MessengerAgent."
                
                return f"✓ Auto-compliance: {message}\n✓ Updated: travel_ready=True, status='ReadyForSubmission'{notification_note}"
            else:
                return f"✗ Compliance check failed: {message}\n✗ No updates made."
        except Exception as e:
            db.rollback()
            return f"Error in auto-compliance check: {str(e)}"
        finally:
            db.close()

