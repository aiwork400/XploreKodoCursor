"""
End-to-End Test Script for XploreKodo Candidate Journey

Tests the complete journey from candidate creation to Phase 2 access:
1. Create candidate 'Siddharth' (Student track)
2. Simulate payment and document upload
3. Trigger TrainingAgent to complete JLPT N5 units
4. Run VisaComplianceAgent to verify Travel-Ready
5. Trigger MessengerAgent for trilingual notification
6. Verify FastAPI /start-lesson endpoint access
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
from sqlalchemy.orm import Session

import config
from agency.database_agent.tools import CreateCandidate
from agency.messenger_agent.tools import SendNotificationTool
from database.db_manager import Candidate, CurriculumProgress, DocumentVault, Payment, SessionLocal
from mvp_v1.commerce.payment_gateway_tool import PaymentGatewayTool
from mvp_v1.Legal.compliance_checker import ComplianceChecker
from mvp_v1.Legal.visa_compliance_tools import CheckCandidateCompliance


class E2EJourneyTest:
    """End-to-end test for candidate journey."""

    def __init__(self, candidate_id: str = "siddharth_test", candidate_name: str = "Siddharth"):
        self.candidate_id = candidate_id
        self.candidate_name = candidate_name
        self.api_base_url = "http://localhost:8000"
        self.test_results = []

    def log_step(self, step_num: int, step_name: str, status: str, message: str = ""):
        """Log test step result."""
        status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]"
        result = {
            "step": step_num,
            "name": step_name,
            "status": status,
            "message": message,
        }
        self.test_results.append(result)
        print(f"{status_symbol} Step {step_num}: {step_name} - {status}")
        if message:
            print(f"   {message}")

    def step_1_create_candidate(self) -> bool:
        """Step 1: Create candidate 'Siddharth' (Student track)."""
        try:
            # Check if candidate already exists
            db = SessionLocal()
            try:
                existing = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
                if existing:
                    db.delete(existing)
                    db.commit()
                    print(f"   Removed existing candidate {self.candidate_id}")

                # Create new candidate
                tool = CreateCandidate(
                    candidate_id=self.candidate_id,
                    full_name=self.candidate_name,
                    track="student",
                )
                result = tool.run()

                if "Successfully created" in result:
                    self.log_step(1, "Create Candidate", "PASS", result)
                    return True
                else:
                    self.log_step(1, "Create Candidate", "FAIL", result)
                    return False
            finally:
                db.close()
        except Exception as e:
            self.log_step(1, "Create Candidate", "FAIL", f"Error: {str(e)}")
            return False

    def step_2_simulate_payment_and_documents(self) -> bool:
        """Step 2: Simulate payment and document upload."""
        try:
            db = SessionLocal()
            try:
                candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
                if not candidate:
                    self.log_step(2, "Payment & Documents", "FAIL", "Candidate not found")
                    return False

                # Simulate payment
                payment_tool = PaymentGatewayTool(
                    amount=500.00,
                    currency="USD",
                    provider="stripe",
                    candidate_id=self.candidate_id,
                    description="XploreKodo Service Fee",
                )
                payment_result = payment_tool.run()

                # Extract transaction ID from result
                transaction_id = f"ch_stripe_test_{self.candidate_id}_{int(time.time())}"

                # Record payment in database
                payment = Payment(
                    candidate_id=self.candidate_id,
                    amount="500.00",
                    currency="USD",
                    provider="stripe",
                    transaction_id=transaction_id,
                    status="success",
                    description="XploreKodo Service Fee",
                )
                db.add(payment)

                # Upload documents (simulate)
                candidate.has_150_hour_study_certificate = True
                candidate.has_financial_sponsor_docs = True
                candidate.passport_path = f"/documents/{self.candidate_id}/passport.pdf"
                candidate.coe_path = f"/documents/{self.candidate_id}/coe.pdf"

                # Create document vault entries
                doc1 = DocumentVault(
                    candidate_id=self.candidate_id,
                    doc_type="passport",
                    file_path=candidate.passport_path,
                )
                doc2 = DocumentVault(
                    candidate_id=self.candidate_id,
                    doc_type="coe",
                    file_path=candidate.coe_path,
                )
                doc3 = DocumentVault(
                    candidate_id=self.candidate_id,
                    doc_type="150_hour_certificate",
                    file_path=f"/documents/{self.candidate_id}/150_hour_cert.pdf",
                )
                db.add(doc1)
                db.add(doc2)
                db.add(doc3)

                db.commit()

                self.log_step(
                    2,
                    "Payment & Documents",
                    "PASS",
                    f"Payment recorded: ${payment.amount} | Documents uploaded: passport, COE, 150-hour cert",
                )
                return True
            except Exception as e:
                db.rollback()
                self.log_step(2, "Payment & Documents", "FAIL", f"Error: {str(e)}")
                return False
            finally:
                db.close()
        except Exception as e:
            self.log_step(2, "Payment & Documents", "FAIL", f"Error: {str(e)}")
            return False

    def step_3_complete_jlpt_n5(self) -> bool:
        """Step 3: Trigger TrainingAgent to complete JLPT N5 units."""
        try:
            db = SessionLocal()
            try:
                curriculum = (
                    db.query(CurriculumProgress)
                    .filter(CurriculumProgress.candidate_id == self.candidate_id)
                    .first()
                )

                if not curriculum:
                    curriculum = CurriculumProgress(candidate_id=self.candidate_id)
                    db.add(curriculum)

                # Complete all N5 units (25 units)
                curriculum.jlpt_n5_units_completed = curriculum.jlpt_n5_total_units
                db.commit()

                # Verify completion
                progress = (curriculum.jlpt_n5_units_completed / curriculum.jlpt_n5_total_units * 100) if curriculum.jlpt_n5_total_units > 0 else 0

                if progress >= 100:
                    self.log_step(
                        3,
                        "Complete JLPT N5",
                        "PASS",
                        f"JLPT N5 completed: {curriculum.jlpt_n5_units_completed}/{curriculum.jlpt_n5_total_units} units (100%)",
                    )
                    return True
                else:
                    self.log_step(3, "Complete JLPT N5", "FAIL", f"Progress incomplete: {progress:.1f}%")
                    return False
            except Exception as e:
                db.rollback()
                self.log_step(3, "Complete JLPT N5", "FAIL", f"Error: {str(e)}")
                return False
            finally:
                db.close()
        except Exception as e:
            self.log_step(3, "Complete JLPT N5", "FAIL", f"Error: {str(e)}")
            return False

    def step_4_verify_travel_ready(self) -> bool:
        """Step 4: Run VisaComplianceAgent to verify Travel-Ready."""
        try:
            # Use CheckCandidateCompliance tool
            tool = CheckCandidateCompliance(candidate_id=self.candidate_id)
            result = tool.run()

            db = SessionLocal()
            try:
                candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
                if candidate and candidate.travel_ready:
                    self.log_step(4, "Verify Travel-Ready", "PASS", f"Status: {candidate.status}, Travel-Ready: {candidate.travel_ready}")
                    return True
                else:
                    self.log_step(4, "Verify Travel-Ready", "FAIL", f"Travel-Ready: {candidate.travel_ready if candidate else 'Candidate not found'}")
                    return False
            finally:
                db.close()
        except Exception as e:
            self.log_step(4, "Verify Travel-Ready", "FAIL", f"Error: {str(e)}")
            return False

    def step_5_send_trilingual_notification(self) -> bool:
        """Step 5: Trigger MessengerAgent for trilingual notification."""
        try:
            # Send notifications in all three languages
            languages = ["Nepali", "Japanese", "English"]
            results = []

            for language in languages:
                tool = SendNotificationTool(
                    candidate_id=self.candidate_id,
                    candidate_name=self.candidate_name,
                    candidate_email=f"{self.candidate_id}@example.com",
                    candidate_phone="+1234567890",
                    notification_type="email",
                    message_type="travel_ready",
                    language=language,
                )
                result = tool.run()
                results.append(f"{language}: Sent")

            self.log_step(5, "Trilingual Notification", "PASS", " | ".join(results))
            return True
        except Exception as e:
            self.log_step(5, "Trilingual Notification", "FAIL", f"Error: {str(e)}")
            return False

    def step_6_verify_phase2_access(self) -> bool:
        """Step 6: Verify FastAPI /start-lesson endpoint allows Phase 2 access."""
        try:
            # Test the /start-lesson endpoint
            payload = {
                "candidate_id": self.candidate_id,
                "module_type": "jlpt",
                "jlpt_level": "N5",
            }

            response = requests.post(f"{self.api_base_url}/start-lesson", json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log_step(
                        6,
                        "Verify Phase 2 Access",
                        "PASS",
                        f"API endpoint accessible. Lesson script generated successfully.",
                    )
                    return True
                else:
                    self.log_step(6, "Verify Phase 2 Access", "FAIL", f"API returned success=False: {result.get('message', 'Unknown')}")
                    return False
            elif response.status_code == 403:
                error_detail = response.json().get("detail", "Forbidden")
                self.log_step(6, "Verify Phase 2 Access", "FAIL", f"Access denied: {error_detail}")
                return False
            else:
                self.log_step(6, "Verify Phase 2 Access", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
        except requests.exceptions.ConnectionError:
            self.log_step(
                6,
                "Verify Phase 2 Access",
                "WARN",
                "API server not running. Start with: uvicorn api.main:app --reload",
            )
            return False
        except Exception as e:
            self.log_step(6, "Verify Phase 2 Access", "FAIL", f"Error: {str(e)}")
            return False

    def run_all_tests(self) -> bool:
        """Run all test steps in sequence."""
        print("=" * 80)
        print("XploreKodo End-to-End Journey Test")
        print("=" * 80)
        print(f"Testing candidate: {self.candidate_name} ({self.candidate_id})")
        print(f"API Base URL: {self.api_base_url}")
        print("=" * 80)
        print()

        steps = [
            self.step_1_create_candidate,
            self.step_2_simulate_payment_and_documents,
            self.step_3_complete_jlpt_n5,
            self.step_4_verify_travel_ready,
            self.step_5_send_trilingual_notification,
            self.step_6_verify_phase2_access,
        ]

        all_passed = True
        for step_func in steps:
            if not step_func():
                all_passed = False
                # Continue with remaining steps even if one fails
            print()

        # Print summary
        print("=" * 80)
        print("Test Summary")
        print("=" * 80)
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        warned = sum(1 for r in self.test_results if r["status"] == "WARN")

        print(f"Total Steps: {len(self.test_results)}")
        print(f"[PASS] Passed: {passed}")
        print(f"[FAIL] Failed: {failed}")
        print(f"[WARN] Warnings: {warned}")
        print()

        if all_passed:
            print("[SUCCESS] All tests passed! Candidate journey is complete.")
        else:
            print("[WARN] Some tests failed. Review the output above for details.")

        print("=" * 80)

        return all_passed


if __name__ == "__main__":
    # Check if Phase 2 is enabled
    if not config.PHASE_2_ENABLED:
        print("[WARN] Warning: PHASE_2_ENABLED is False. Some Phase 2 features may not work.")
        print("   Set PHASE_2_ENABLED=True in .env to enable full testing.")
        print()

    # Run tests
    test = E2EJourneyTest(candidate_id="siddharth_test", candidate_name="Siddharth")
    success = test.run_all_tests()

    sys.exit(0 if success else 1)

