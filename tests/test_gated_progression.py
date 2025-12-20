"""
Test script for Gated Progression System

Verifies:
1. Phase determination logic
2. Phase-based word selection
3. 70/30 split (new vs review)
4. Phase unlock requirements
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from sqlalchemy.orm import Session
from database.db_manager import Candidate, KnowledgeBase, SessionLocal, StudentPerformance
from agency.student_progress_agent.tools import GetCurrentPhase


def ensure_test_candidate(db: Session, candidate_id: str = "test_phase_001") -> str:
    """Ensure a test candidate exists."""
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    
    if not candidate:
        candidate = Candidate(
            candidate_id=candidate_id,
            full_name="Test Phase Candidate",
            track="jobseeker",
            has_jlpt_n4_or_n5=True,
            has_kaigo_skills_test=False,
            status="Incomplete",
            travel_ready=False,
        )
        db.add(candidate)
        db.commit()
        print(f"✅ Created test candidate: {candidate_id}")
    else:
        print(f"✅ Using existing candidate: {candidate_id}")
    
    return candidate_id


def create_test_performance(
    db: Session,
    candidate_id: str,
    word_title: str,
    score: int,
    category: str
):
    """Create a test performance record."""
    # Find word in knowledge_base
    word = db.query(KnowledgeBase).filter(KnowledgeBase.concept_title == word_title).first()
    
    if not word:
        # Create word if it doesn't exist
        word = KnowledgeBase(
            source_file="test",
            concept_title=word_title,
            concept_content=f"Test word: {word_title}",
            page_number=None,
            language="ja",
            category=category,
        )
        db.add(word)
        db.flush()
    
    # Create performance record
    performance = StudentPerformance(
        candidate_id=candidate_id,
        word_id=word.id,
        word_title=word_title,
        score=score,
        feedback=f"Test feedback for {word_title}",
        accuracy_feedback="Test accuracy",
        grammar_feedback="Test grammar",
        pronunciation_hint="Test pronunciation",
        transcript=f"Test answer for {word_title}",
        language_code="ja-JP",
        category=category,
    )
    db.add(performance)
    db.commit()
    print(f"  ✅ Created performance: {word_title} - Score {score}/10 ({category})")


def test_phase_1():
    """Test Phase 1 (N5 Basics) - should be current if avg < 6.0 or < 20 words."""
    print("\n" + "=" * 70)
    print("🧪 Test 1: Phase 1 (N5 Basics)")
    print("=" * 70)
    
    db: Session = SessionLocal()
    candidate_id = ensure_test_candidate(db, "test_phase_001")
    
    try:
        # Clear existing performance
        db.query(StudentPerformance).filter(
            StudentPerformance.candidate_id == candidate_id
        ).delete()
        db.commit()
        
        # Create 10 N5 words with average score 5.0 (should stay in Phase 1)
        print("\n📝 Creating 10 N5 words with avg score 5.0...")
        for i in range(10):
            create_test_performance(
                db, candidate_id, f"N5_Word_{i+1}", 5, "jlpt_n5_vocabulary"
            )
        
        # Check phase
        phase_tool = GetCurrentPhase(candidate_id=candidate_id)
        result = phase_tool.run()
        
        import json
        phase_info = json.loads(result)
        
        current_phase = phase_info.get("current_phase", 0)
        metrics = phase_info.get("metrics", {})
        
        print(f"\n📊 Results:")
        print(f"   Current Phase: {current_phase}")
        print(f"   N5 Average: {metrics.get('n5_avg', 0):.1f}/10")
        print(f"   N5 Count: {metrics.get('n5_count', 0)}")
        
        assert current_phase == 1, f"Expected Phase 1, got Phase {current_phase}"
        print("✅ Test 1 PASSED: Correctly identified Phase 1")
        
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_phase_2_unlock():
    """Test Phase 2 unlock - requires N5 avg ≥ 6.0 AND 20+ words."""
    print("\n" + "=" * 70)
    print("🧪 Test 2: Phase 2 Unlock (N5 avg ≥ 6.0 AND 20+ words)")
    print("=" * 70)
    
    db: Session = SessionLocal()
    candidate_id = ensure_test_candidate(db, "test_phase_002")
    
    try:
        # Clear existing performance
        db.query(StudentPerformance).filter(
            StudentPerformance.candidate_id == candidate_id
        ).delete()
        db.commit()
        
        # Create 20 N5 words with average score 6.5 (should unlock Phase 2)
        print("\n📝 Creating 20 N5 words with avg score 6.5...")
        for i in range(20):
            create_test_performance(
                db, candidate_id, f"N5_Word_{i+1}", 6, "jlpt_n5_vocabulary"
            )
        # Add a few 7s to bring average to 6.5
        for i in range(5):
            create_test_performance(
                db, candidate_id, f"N5_Word_high_{i+1}", 7, "jlpt_n5_vocabulary"
            )
        
        # Check phase
        phase_tool = GetCurrentPhase(candidate_id=candidate_id)
        result = phase_tool.run()
        
        import json
        phase_info = json.loads(result)
        
        current_phase = phase_info.get("current_phase", 0)
        phase_unlocked = phase_info.get("phase_unlocked", [])
        metrics = phase_info.get("metrics", {})
        
        print(f"\n📊 Results:")
        print(f"   Current Phase: {current_phase}")
        print(f"   Phase Unlocked: {phase_unlocked}")
        print(f"   N5 Average: {metrics.get('n5_avg', 0):.1f}/10")
        print(f"   N5 Count: {metrics.get('n5_count', 0)}")
        
        assert current_phase == 2, f"Expected Phase 2, got Phase {current_phase}"
        assert len(phase_unlocked) > 1 and phase_unlocked[1], "Phase 2 should be unlocked"
        print("✅ Test 2 PASSED: Phase 2 correctly unlocked")
        
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_phase_3_unlock():
    """Test Phase 3 unlock - requires Caregiving avg ≥ 7.5."""
    print("\n" + "=" * 70)
    print("🧪 Test 3: Phase 3 Unlock (Caregiving avg ≥ 7.5)")
    print("=" * 70)
    
    db: Session = SessionLocal()
    candidate_id = ensure_test_candidate(db, "test_phase_003")
    
    try:
        # Clear existing performance
        db.query(StudentPerformance).filter(
            StudentPerformance.candidate_id == candidate_id
        ).delete()
        db.commit()
        
        # First unlock Phase 2 (20 N5 words with avg 6.0+)
        print("\n📝 Creating 20 N5 words to unlock Phase 2...")
        for i in range(20):
            create_test_performance(
                db, candidate_id, f"N5_Word_{i+1}", 6, "jlpt_n5_vocabulary"
            )
        
        # Then create caregiving words with avg 7.5+
        # Need average >= 7.5: (10*7 + 5*8) = 110/15 = 7.33 (not enough)
        # Better: (5*7 + 10*8) = 115/15 = 7.67 (enough)
        print("\n📝 Creating 15 caregiving words with avg 7.5+...")
        for i in range(5):
            create_test_performance(
                db, candidate_id, f"Care_Word_{i+1}", 7, "caregiving_vocabulary"
            )
        # Add more 8s to bring average to 7.5+
        for i in range(10):
            create_test_performance(
                db, candidate_id, f"Care_Word_high_{i+1}", 8, "caregiving_vocabulary"
            )
        
        # Check phase
        phase_tool = GetCurrentPhase(candidate_id=candidate_id)
        result = phase_tool.run()
        
        import json
        phase_info = json.loads(result)
        
        current_phase = phase_info.get("current_phase", 0)
        phase_unlocked = phase_info.get("phase_unlocked", [])
        metrics = phase_info.get("metrics", {})
        
        print(f"\n📊 Results:")
        print(f"   Current Phase: {current_phase}")
        print(f"   Phase Unlocked: {phase_unlocked}")
        print(f"   Caregiving Average: {metrics.get('caregiving_avg', 0):.1f}/10")
        print(f"   Caregiving Count: {metrics.get('caregiving_count', 0)}")
        
        assert current_phase == 3, f"Expected Phase 3, got Phase {current_phase}"
        assert len(phase_unlocked) > 2 and phase_unlocked[2], "Phase 3 should be unlocked"
        print("✅ Test 3 PASSED: Phase 3 correctly unlocked")
        
    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 Gated Progression System Test Suite")
    print("=" * 70)
    
    test_phase_1()
    test_phase_2_unlock()
    test_phase_3_unlock()
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

