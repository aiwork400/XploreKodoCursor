"""
Test Script for Language Coaching Grading Logic

Tests the LanguageCoachAgent's grading tool with a simulated Japanese answer.
Scenario: Candidate provides answer for '病院' (Byouin) with transcription 'Kore wa byouin desu.'
"""

from __future__ import annotations

import base64
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

import config
from database.db_manager import Candidate, CurriculumProgress, KnowledgeBase, SessionLocal
from agency.training_agent.language_coaching_tool import LanguageCoachingTool


def lookup_word_in_knowledge_base(word: str, db: Session) -> dict | None:
    """
    Look up a word in the knowledge_base table.
    
    Args:
        word: Japanese word to look up
        db: Database session
    
    Returns:
        Dictionary with word information or None if not found
    """
    entry = db.query(KnowledgeBase).filter(
        KnowledgeBase.concept_title == word
    ).first()
    
    if entry:
        return {
            "concept_title": entry.concept_title,
            "concept_content": entry.concept_content,
            "language": entry.language,
            "category": entry.category,
        }
    return None


def create_dummy_audio_base64() -> str:
    """
    Create a dummy base64-encoded audio string for testing.
    Since we're testing with a known transcript, this is just a placeholder.
    """
    # Create minimal WAV header (44 bytes) + some dummy audio data
    # This is just to satisfy the tool's requirement for audio_base64
    dummy_wav = b'RIFF' + b'\x00' * 40
    return base64.b64encode(dummy_wav).decode('utf-8')


def ensure_test_candidate(db: Session) -> str:
    """
    Ensure a test candidate exists in the database.
    
    Returns:
        candidate_id of the test candidate
    """
    candidate_id = "test_coach_001"
    
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    
    if not candidate:
        candidate = Candidate(
            candidate_id=candidate_id,
            full_name="Test Candidate (Language Coach)",
            track="jobseeker",
            has_jlpt_n4_or_n5=True,
            has_kaigo_skills_test=False,
            status="Incomplete",
            travel_ready=False,
        )
        db.add(candidate)
        db.flush()
        print(f"✅ Created test candidate: {candidate_id}")
    else:
        print(f"✅ Using existing test candidate: {candidate_id}")
    
    return candidate_id


def main():
    """Main test function."""
    print("=" * 70)
    print("🧪 Language Coaching Grading Test")
    print("=" * 70)
    print()
    
    # Test parameters
    test_word = "病院"  # Byouin (Hospital)
    test_transcript = "Kore wa byouin desu."  # "This is a hospital."
    test_language = "ja-JP"
    
    print(f"📝 Test Scenario:")
    print(f"   Word: {test_word} (Byouin - Hospital)")
    print(f"   Candidate's Answer (Transcribed): '{test_transcript}'")
    print(f"   Language: {test_language}")
    print()
    
    db: Session = SessionLocal()
    
    try:
        # Step 1: Look up word in knowledge_base
        print("🔍 Step 1: Looking up '病院' in knowledge_base...")
        word_info = lookup_word_in_knowledge_base(test_word, db)
        
        if word_info:
            print(f"✅ Found in knowledge_base:")
            print(f"   Title: {word_info['concept_title']}")
            print(f"   Category: {word_info.get('category', 'N/A')}")
            print(f"   Content Preview: {word_info['concept_content'][:100]}...")
            
            # Extract expected answer context from knowledge_base
            expected_answer = word_info['concept_content']
        else:
            print(f"⚠️  Word '{test_word}' not found in knowledge_base")
            print("   Using default expected answer context...")
            expected_answer = "病院 (Byouin) means 'Hospital' in English. In Nepali, it is 'अस्पताल' (Aspatal)."
        
        print()
        
        # Step 2: Ensure test candidate exists
        print("👤 Step 2: Setting up test candidate...")
        candidate_id = ensure_test_candidate(db)
        db.commit()
        print()
        
        # Step 3: Create a mock audio (we'll bypass STT by providing the transcript directly)
        # For this test, we'll create a minimal tool instance and call the grading method directly
        print("🎤 Step 3: Testing Language Coaching Grading...")
        print("   (Using direct grading method with known transcript)")
        print()
        
        # Create tool instance
        tool = LanguageCoachingTool(
            candidate_id=candidate_id,
            audio_base64=create_dummy_audio_base64(),
            language_code=test_language,
            question_id="test_byouin_001",
            expected_answer=expected_answer,
        )
        
        # Since we want to test with a known transcript, we'll call the grading method directly
        # This bypasses STT which might not be configured
        print("🤖 Calling Gemini AI for grading...")
        grading_result = tool._grade_response_with_gemini(
            transcript=test_transcript,
            language=test_language,
            expected_answer=expected_answer
        )
        
        print()
        print("=" * 70)
        print("📊 AI GRADING RESULTS")
        print("=" * 70)
        print()
        
        # Display results
        grade = grading_result.get("grade", 0)
        grade_emoji = "🟢" if grade >= 8 else "🟡" if grade >= 6 else "🔴"
        
        print(f"{grade_emoji} Overall Grade: {grade}/10")
        print()
        
        print("✅ Accuracy Feedback:")
        print(f"   {grading_result.get('accuracy_feedback', 'N/A')}")
        print()
        
        print("📝 Grammar Feedback:")
        print(f"   {grading_result.get('grammar_feedback', 'N/A')}")
        print()
        
        print("🎯 Pronunciation Hint (Socratic Tip):")
        print(f"   {grading_result.get('pronunciation_hint', 'N/A')}")
        print()
        
        print("=" * 70)
        print("✅ Test Complete!")
        print("=" * 70)
        
        # Show Socratic coaching tip
        print()
        print("💡 Socratic Coaching Tip:")
        if grade >= 8:
            print("   Great job! You correctly identified the word. Consider expanding your answer")
            print("   with more context about hospitals in caregiving situations.")
        elif grade >= 6:
            print("   Good attempt! You're on the right track. Think about:")
            print("   - How would you use this word in a caregiving context?")
            print("   - What other related words do you know?")
        else:
            print("   Let's work on this together. Consider:")
            print("   - What does '病院' mean in the context of caregiving?")
            print("   - Can you think of a sentence where you would use this word?")
            print("   - How does this relate to your caregiving training?")
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

