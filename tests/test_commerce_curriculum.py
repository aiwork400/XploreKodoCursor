"""
TDD tests for Commerce & Curriculum Hub.

Verifies:
- PaymentGatewayTool functionality
- CurriculumTracker progress tracking
- Phase 2 AR-VR hooks remain dormant
"""

from __future__ import annotations

import pytest

import config
from mvp_v1.commerce.payment_gateway_tool import PaymentGatewayTool
from mvp_v1.skills.curriculum_tracker import CurriculumTracker


def test_payment_gateway_stripe() -> None:
    """Verify PaymentGatewayTool processes Stripe payments."""
    tool = PaymentGatewayTool(
        amount=100.0,
        currency="USD",
        provider="stripe",
        candidate_id="test-001",
        description="Test payment",
    )
    result = tool.run()
    assert "Stripe Payment Processed" in result
    assert "test-001" in result
    assert "100.0" in result


def test_payment_gateway_paypal() -> None:
    """Verify PaymentGatewayTool processes PayPal payments."""
    tool = PaymentGatewayTool(
        amount=50.0,
        currency="USD",
        provider="paypal",
        candidate_id="test-002",
    )
    result = tool.run()
    assert "PayPal Payment Processed" in result
    assert "test-002" in result


def test_curriculum_tracker_initialization() -> None:
    """Verify CurriculumTracker initializes candidate progress."""
    tracker = CurriculumTracker()
    tracker.initialize_candidate("candidate-001")

    progress = tracker.get_progress("candidate-001")
    assert progress is not None
    assert progress.candidate_id == "candidate-001"
    assert "N5" in progress.language
    assert "N4" in progress.language
    assert "N3" in progress.language
    assert len(progress.vocational) > 0
    assert len(progress.professional) > 0


def test_curriculum_tracker_language_progress() -> None:
    """Verify CurriculumTracker updates language progress."""
    tracker = CurriculumTracker()
    tracker.initialize_candidate("candidate-002")
    tracker.update_language_progress("candidate-002", "N5", 15)

    progress = tracker.get_progress("candidate-002")
    assert progress.language["N5"].units_completed == 15


def test_curriculum_tracker_vocational_progress() -> None:
    """Verify CurriculumTracker updates vocational progress."""
    tracker = CurriculumTracker()
    tracker.initialize_candidate("candidate-003")
    tracker.update_vocational_progress("candidate-003", "Kaigo Basics", 10)

    progress = tracker.get_progress("candidate-003")
    kaigo = next(m for m in progress.vocational if m.module_name == "Kaigo Basics")
    assert kaigo.lessons_completed == 10


def test_curriculum_tracker_professional_progress() -> None:
    """Verify CurriculumTracker updates professional progress."""
    tracker = CurriculumTracker()
    tracker.initialize_candidate("candidate-004")
    tracker.update_professional_progress("candidate-004", "AI/ML Fundamentals", 8)

    progress = tracker.get_progress("candidate-004")
    ai_ml = next(
        m for m in progress.professional if m.module_name == "AI/ML Fundamentals"
    )
    assert ai_ml.topics_completed == 8


def test_phase_2_ar_vr_dormant() -> None:
    """Verify Phase 2 AR-VR hooks remain dormant when PHASE_2_ENABLED=False."""
    assert config.PHASE_2_ENABLED is False

    tracker = CurriculumTracker()
    tracker.initialize_candidate("candidate-005")

    # Attempting to record AR-VR session should raise RuntimeError
    with pytest.raises(RuntimeError, match="Phase 2"):
        tracker.record_ar_vr_session("candidate-005")

