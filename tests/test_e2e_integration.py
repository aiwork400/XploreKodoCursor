"""
E2E Integration Test for XploreKodo Platform

Tests the complete pipeline:
1. Knowledge Base (Caregiving & N5 words)
2. LanguageCoachAgent asks a Caregiving question
3. Mock voice transcript response
4. StudentProgressAgent updates score
5. ActivityLogger records event

Validates all three database tables are involved in a single loop.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from database.db_manager import (
    ActivityLog,
    Candidate,
    KnowledgeBase,
    SessionLocal,
    StudentPerformance,
    init_db,
)


def ensure_test_candidate(db: Session) -> str:
    """Ensure a test candidate exists in the database."""
    candidate_id = "test_e2e_candidate"
    
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        candidate = Candidate(
            candidate_id=candidate_id,
            full_name="E2E Test Student",
            track="student",
            status="Active",
        )
        db.add(candidate)
        db.commit()
        print(f"✅ Created test candidate: {candidate_id}")
    else:
        print(f"✅ Using existing test candidate: {candidate_id}")
    
    return candidate_id


def check_and_seed_knowledge_base(db: Session) -> dict:
    """
    Check if knowledge_base has at least 2 Caregiving and 2 N5 words.
    If not, seed them.
    
    Returns:
        dict with counts: {'caregiving': count, 'n5': count}
    """
    # Check existing counts
    caregiving_count = db.query(KnowledgeBase).filter(
        KnowledgeBase.category == "caregiving_vocabulary"
    ).count()
    
    n5_count = db.query(KnowledgeBase).filter(
        KnowledgeBase.category == "jlpt_n5_vocabulary"
    ).count()
    
    print(f"\n📊 Current Knowledge Base Status:")
    print(f"   Caregiving words: {caregiving_count}")
    print(f"   N5 words: {n5_count}")
    
    # Seed if needed
    caregiving_words = [
        ("病院", "Hospital - A medical facility where patients receive treatment."),
        ("看護師", "Nurse - A healthcare professional who provides patient care."),
    ]
    
    n5_words = [
        ("こんにちは", "Hello - A common greeting used during the day."),
        ("ありがとう", "Thank you - An expression of gratitude."),
    ]
    
    # Seed Caregiving words if needed
    if caregiving_count < 2:
        print(f"\n🌱 Seeding {2 - caregiving_count} Caregiving words...")
        for word, content in caregiving_words[:2 - caregiving_count]:
            existing = db.query(KnowledgeBase).filter(
                KnowledgeBase.concept_title == word,
                KnowledgeBase.category == "caregiving_vocabulary"
            ).first()
            
            if not existing:
                kb_entry = KnowledgeBase(
                    source_file="e2e_test_seed",
                    concept_title=word,
                    concept_content=f"Word: {word}\nEnglish: {content}",
                    language="ja",
                    category="caregiving_vocabulary",
                )
                db.add(kb_entry)
                print(f"   ✅ Added: {word}")
        
        db.commit()
        caregiving_count = 2
    
    # Seed N5 words if needed
    if n5_count < 2:
        print(f"\n🌱 Seeding {2 - n5_count} N5 words...")
        for word, content in n5_words[:2 - n5_count]:
            existing = db.query(KnowledgeBase).filter(
                KnowledgeBase.concept_title == word,
                KnowledgeBase.category == "jlpt_n5_vocabulary"
            ).first()
            
            if not existing:
                kb_entry = KnowledgeBase(
                    source_file="e2e_test_seed",
                    concept_title=word,
                    concept_content=f"Word: {word}\nEnglish: {content}",
                    language="ja",
                    category="jlpt_n5_vocabulary",
                )
                db.add(kb_entry)
                print(f"   ✅ Added: {word}")
        
        db.commit()
        n5_count = 2
    
    return {"caregiving": caregiving_count, "n5": n5_count}


def simulate_caregiving_question(db: Session, candidate_id: str) -> dict:
    """
    Simulate LanguageCoachAgent asking a Caregiving question using SocraticQuestioningTool.
    
    Returns:
        dict with question_id, word_title, expected_answer
    """
    print("\n" + "=" * 60)
    print("🎓 Step 1: LanguageCoachAgent asks Caregiving question")
    print("=" * 60)
    
    # Get a caregiving word from knowledge_base
    caregiving_word = db.query(KnowledgeBase).filter(
        KnowledgeBase.category == "caregiving_vocabulary"
    ).first()
    
    if not caregiving_word:
        raise Exception("No caregiving words found in knowledge_base!")
    
    word_title = caregiving_word.concept_title
    word_content = caregiving_word.concept_content
    
    print(f"📚 Selected word: {word_title}")
    print(f"📝 Content: {word_content[:100]}...")
    
    # Simulate SocraticQuestioningTool asking a question
    # In a real scenario, this would use the SocraticQuestioningTool.run() method
    question = f"Please explain what '{word_title}' means in a caregiving context."
    expected_answer = word_content
    
    print(f"❓ Question: {question}")
    print(f"✅ Expected answer context: {expected_answer[:100]}...")
    
    return {
        "question_id": "e2e_test_question_1",
        "word_title": word_title,
        "expected_answer": expected_answer,
        "question": question,
    }


def mock_voice_transcript() -> tuple[str, str]:
    """
    Mock a voice transcript response.
    
    Returns:
        tuple of (transcript_text, base64_audio_mock)
    """
    print("\n" + "=" * 60)
    print("🎤 Step 2: Mock voice transcript response")
    print("=" * 60)
    
    # Mock transcript - a student's response in Japanese
    transcript = "病院は患者を治療する医療施設です。"
    print(f"📝 Mock transcript: {transcript}")
    
    # Create a mock base64 audio (just a placeholder - won't be used for actual STT)
    mock_audio_base64 = base64.b64encode(b"mock_audio_data").decode("utf-8")
    
    return transcript, mock_audio_base64


def simulate_grading_pipeline(
    db: Session,
    candidate_id: str,
    transcript: str,
    word_title: str,
    expected_answer: str,
    mock_audio_base64: str,
) -> dict:
    """
    Simulate the complete grading pipeline:
    - LanguageCoachingTool grades the response
    - RecordProgress saves to student_performance
    - ActivityLogger records the event
    
    Returns:
        dict with grading_result, performance_record, activity_log
    """
    print("\n" + "=" * 60)
    print("📊 Step 3: Complete Grading Pipeline")
    print("=" * 60)
    
    # Mock grading result (in real scenario, this would come from Gemini)
    grading_result = {
        "grade": 7,
        "accuracy_feedback": "Good understanding of the word. The explanation is clear and accurate.",
        "grammar_feedback": "Minor grammar improvements needed, but overall structure is correct.",
        "pronunciation_hint": "Focus on the pronunciation of '病院' (byouin).",
    }
    
    print(f"✅ AI Grading Result:")
    print(f"   Score: {grading_result['grade']}/10")
    print(f"   Accuracy: {grading_result['accuracy_feedback'][:60]}...")
    
    # Step 3a: RecordProgress (StudentProgressAgent)
    print("\n📝 Step 3a: Recording performance in student_performance table...")
    from agency.student_progress_agent.tools import RecordProgress
    
    record_tool = RecordProgress(
        candidate_id=candidate_id,
        word_title=word_title,
        score=grading_result["grade"],
        feedback=f"E2E test - {grading_result['accuracy_feedback'][:50]}",
        accuracy_feedback=grading_result["accuracy_feedback"],
        grammar_feedback=grading_result["grammar_feedback"],
        pronunciation_hint=grading_result["pronunciation_hint"],
        transcript=transcript,
        language_code="ja-JP",
        category="caregiving_vocabulary",
    )
    
    record_result = record_tool.run()
    print(f"   {record_result}")
    
    # Step 3b: ActivityLogger
    print("\n📋 Step 3b: Logging activity in activity_logs table...")
    from utils.activity_logger import ActivityLogger
    
    ActivityLogger.log_grading(
        candidate_id=candidate_id,
        word_title=word_title,
        score=grading_result["grade"],
        transcript=transcript,
        feedback={
            "accuracy": grading_result["accuracy_feedback"],
            "grammar": grading_result["grammar_feedback"],
            "pronunciation": grading_result["pronunciation_hint"],
        },
    )
    print("   ✅ Activity logged successfully")
    
    return {
        "grading_result": grading_result,
        "record_result": record_result,
    }


def generate_system_health_report(db: Session, candidate_id: str, word_title: str) -> None:
    """
    Generate and print a System Health Report showing all three tables were involved.
    """
    print("\n" + "=" * 80)
    print("🏥 SYSTEM HEALTH REPORT")
    print("=" * 80)
    
    # 1. Knowledge Base Check
    print("\n📚 1. KNOWLEDGE_BASE TABLE")
    print("-" * 80)
    kb_entry = db.query(KnowledgeBase).filter(
        KnowledgeBase.concept_title == word_title
    ).first()
    
    if kb_entry:
        print(f"   ✅ Word found: {kb_entry.concept_title}")
        print(f"   📂 Category: {kb_entry.category}")
        print(f"   📄 Content preview: {kb_entry.concept_content[:80]}...")
        print(f"   🆔 ID: {kb_entry.id}")
    else:
        print(f"   ❌ Word '{word_title}' NOT FOUND in knowledge_base!")
    
    # 2. Student Performance Check
    print("\n📊 2. STUDENT_PERFORMANCE TABLE")
    print("-" * 80)
    performance = db.query(StudentPerformance).filter(
        StudentPerformance.candidate_id == candidate_id,
        StudentPerformance.word_title == word_title,
    ).order_by(StudentPerformance.created_at.desc()).first()
    
    if performance:
        print(f"   ✅ Performance record found")
        print(f"   👤 Candidate: {performance.candidate_id}")
        print(f"   📝 Word: {performance.word_title}")
        print(f"   ⭐ Score: {performance.score}/10")
        print(f"   📅 Created: {performance.created_at}")
        print(f"   🆔 ID: {performance.id}")
        print(f"   🔗 Word ID (FK): {performance.word_id}")
    else:
        print(f"   ❌ No performance record found for '{word_title}'!")
    
    # 3. Activity Logs Check
    print("\n📋 3. ACTIVITY_LOGS TABLE")
    print("-" * 80)
    activity_log = db.query(ActivityLog).filter(
        ActivityLog.user_id == candidate_id,
        ActivityLog.event_type == "Grading",
    ).order_by(ActivityLog.timestamp.desc()).first()
    
    if activity_log:
        print(f"   ✅ Activity log found")
        print(f"   👤 User ID: {activity_log.user_id}")
        print(f"   📝 Event Type: {activity_log.event_type}")
        print(f"   ⚠️  Severity: {activity_log.severity}")
        print(f"   💬 Message: {activity_log.message}")
        print(f"   📅 Timestamp: {activity_log.timestamp}")
        print(f"   🆔 ID: {activity_log.id}")
        
        if activity_log.event_metadata:
            metadata = activity_log.event_metadata
            print(f"   📦 Metadata:")
            print(f"      - Word: {metadata.get('word_title', 'N/A')}")
            print(f"      - Score: {metadata.get('score', 'N/A')}")
            print(f"      - Transcript: {metadata.get('transcript', 'N/A')[:50]}...")
    else:
        print(f"   ❌ No activity log found for candidate '{candidate_id}'!")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 INTEGRATION SUMMARY")
    print("=" * 80)
    
    all_tables_involved = all([
        kb_entry is not None,
        performance is not None,
        activity_log is not None,
    ])
    
    if all_tables_involved:
        print("✅ SUCCESS: All three database tables were involved in the pipeline!")
        print("\n   ✓ knowledge_base: Word retrieved for question")
        print("   ✓ student_performance: Score recorded")
        print("   ✓ activity_logs: Event logged for admin monitoring")
        print("\n🎉 E2E Integration Test PASSED!")
    else:
        print("❌ FAILURE: Not all tables were involved!")
        if not kb_entry:
            print("   ✗ knowledge_base: Word not found")
        if not performance:
            print("   ✗ student_performance: Record not found")
        if not activity_log:
            print("   ✗ activity_logs: Log not found")
        print("\n⚠️  E2E Integration Test FAILED!")
    
    print("=" * 80)


def main():
    """Main E2E integration test."""
    print("=" * 80)
    print("🧪 E2E INTEGRATION TEST - XploreKodo Platform")
    print("=" * 80)
    print("\nThis test validates the complete pipeline:")
    print("  1. Knowledge Base (Caregiving & N5 words)")
    print("  2. LanguageCoachAgent asks Caregiving question")
    print("  3. Mock voice transcript response")
    print("  4. StudentProgressAgent updates score")
    print("  5. ActivityLogger records event")
    print("\n" + "=" * 80)
    
    # Initialize database
    print("\n🔧 Initializing database...")
    init_db()
    print("✅ Database initialized")
    
    db: Session = SessionLocal()
    try:
        # Step 0: Ensure test candidate exists
        candidate_id = ensure_test_candidate(db)
        
        # Step 1: Check and seed knowledge_base
        kb_counts = check_and_seed_knowledge_base(db)
        if kb_counts["caregiving"] < 2 or kb_counts["n5"] < 2:
            raise Exception("Failed to seed knowledge_base with required words!")
        
        # Step 2: Simulate Caregiving question
        question_data = simulate_caregiving_question(db, candidate_id)
        
        # Step 3: Mock voice transcript
        transcript, mock_audio = mock_voice_transcript()
        
        # Step 4: Simulate grading pipeline
        grading_data = simulate_grading_pipeline(
            db=db,
            candidate_id=candidate_id,
            transcript=transcript,
            word_title=question_data["word_title"],
            expected_answer=question_data["expected_answer"],
            mock_audio_base64=mock_audio,
        )
        
        # Step 5: Generate System Health Report
        generate_system_health_report(db, candidate_id, question_data["word_title"])
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

