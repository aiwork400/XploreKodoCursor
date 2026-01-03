from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import config
from google import genai
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

class GradingInput(BaseModel):
    response: str = Field(description="The student's competency statement")
    candidate_id: Optional[str] = Field(default=None, description="The ID of the candidate")
    track: Optional[str] = Field(default="Academic", description="The track for which the competency is being graded")
    language: Optional[str] = Field(default="en", description="The language of the transcript")
    lesson_name: Optional[str] = Field(default=None, description="The name of the lesson being graded")
    question_start_time: Optional[float] = Field(default=None, description="Timestamp when question was asked (for duration calculation)")
    session_id: Optional[str] = Field(default=None, description="Session ID for grouping related questions")

class CompetencyGradingTool(BaseTool):
    name: str = "competency_grading_tool"
    description: str = "Evaluates student responses for JLPT and Food Tech mastery"
    args_schema: Type[BaseModel] = GradingInput
    
    # Force Initialization: Print statement to verify it is no longer abstract [cite: 2025-12-21]
    # Tool Attribute Fix: Use self.name instead of global name variable [cite: 2025-12-21]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"Tool initialized: {self.name}")
    
    def _run(self, response: str, lesson_name: Optional[str] = None, **kwargs) -> dict:
        """
        Grades the transcript and returns the score and feedback with granular tracking.
        
        The Method: Explicitly accepts lesson_name as an argument [cite: 2025-12-21]
        Granular Tracking: Returns question_word_count, question_duration, sensei_critique [cite: 2025-07-07, 2025-12-21]
        """
        # Extract optional parameters from kwargs
        candidate_id = kwargs.get('candidate_id', None)
        track = kwargs.get('track', 'Academic')
        language = kwargs.get('language', 'en')
        question_start_time = kwargs.get('question_start_time', None)
        session_id = kwargs.get('session_id', None)
        
        # lesson_name is now an explicit parameter, but also check kwargs for backward compatibility
        if lesson_name is None:
            lesson_name = kwargs.get('lesson_name', None)
        
        # Calculate question_duration if start time provided [cite: 2025-12-21]
        question_duration = None
        if question_start_time:
            question_duration = time.time() - question_start_time
        
        # Generate session_id if not provided [cite: 2025-12-21]
        if not session_id:
            session_id = str(uuid4())
        
        if not config.GEMINI_API_KEY:
            return {
                "grade": 5,
                "accuracy_feedback": "Unable to grade: Gemini API not available",
                "grammar_feedback": "Unable to grade: Gemini API not available",
                "pronunciation_hint": "Pronunciation not assessed in text-only grading."
            }

        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        language_map = {
            "en": "English",
            "ne": "Nepali",
            "ja": "Japanese"
        }
        language_name = language_map.get(language, "English")

        # Knowledge Grounding: Look for transcript file matching lesson_name [cite: 2025-12-20, 2025-12-21]
        transcript_content = None
        if lesson_name:
            # Try to find transcript file in assets/transcripts/ directory
            project_root = Path(__file__).parent.parent.parent
            transcripts_dir = project_root / "assets" / "transcripts"
            
            # Normalize lesson_name to filename (remove special chars, spaces to underscores)
            safe_lesson_name = lesson_name.replace(" ", "_").replace(".", "").replace("/", "_").lower()
            
            # Try multiple filename patterns
            possible_files = [
                transcripts_dir / f"{safe_lesson_name}.txt",
                transcripts_dir / f"{lesson_name}.txt",
                transcripts_dir / f"{safe_lesson_name.replace('_', '-')}.txt",
            ]
            
            # Also try with common prefixes/suffixes
            if "n5" in safe_lesson_name.lower() or "n4" in safe_lesson_name.lower() or "n3" in safe_lesson_name.lower():
                # Extract level and base name
                for level in ["n5", "n4", "n3"]:
                    if level in safe_lesson_name.lower():
                        base_name = safe_lesson_name.replace(level, "").strip("_").strip("-")
                        possible_files.extend([
                            transcripts_dir / f"{level}_{base_name}.txt",
                            transcripts_dir / f"{level}/{base_name}.txt",
                            transcripts_dir / f"{level}/{safe_lesson_name}.txt",
                        ])
            
            # Try to read transcript file
            for transcript_file in possible_files:
                if transcript_file.exists():
                    try:
                        transcript_content = transcript_file.read_text(encoding='utf-8').strip()
                        break
                    except Exception as e:
                        print(f"Warning: Could not read transcript file {transcript_file}: {e}")
                        continue
        
        # Fallback: Use default General N5 Vocational Safety guidelines if no transcript found [cite: 2025-12-20]
        if not transcript_content:
            transcript_content = """General N5 Vocational Safety Guidelines:

1. Kitchen Safety Basics:
   - Always wash hands before handling food
   - Use proper cutting techniques to avoid injury
   - Keep work surfaces clean and sanitized
   - Store food at appropriate temperatures

2. Hygiene Standards:
   - Wear clean uniforms and hairnets
   - Follow proper handwashing procedures
   - Maintain personal cleanliness
   - Report any health issues immediately

3. Equipment Safety:
   - Use equipment only after proper training
   - Report malfunctioning equipment
   - Follow manufacturer instructions
   - Keep equipment clean and maintained

4. Food Handling:
   - Follow FIFO (First In, First Out) principles
   - Check expiration dates regularly
   - Maintain proper temperature logs
   - Prevent cross-contamination

These guidelines form the foundation of commercial kitchen safety and should be followed at all times."""
        
        # Context Injection: Inject transcript content into prompt as Primary Study Material [cite: 2025-12-20]
        primary_material_section = ""
        if transcript_content:
            primary_material_section = f"""
**Primary Study Material:**
{transcript_content}

"""
        
        prompt = f"""You are an expert AI language coach. Your task is to grade the following transcript based on its content, grammar, and overall coherence. The user is in the '{track}' track.

{primary_material_section}**Student Response to Grade:**
"{response}"

**Instructions:**
- Grade the student's response based on how well it demonstrates understanding of the Primary Study Material above.
- Provide a single overall grade from 1-10.
- Provide feedback on accuracy (how well it aligns with the study material) and grammar.
- Keep feedback concise and helpful.
- Reference specific points from the Primary Study Material when relevant.
- Sensei Logic: Identify the student's specific area of weakness (e.g., Grammar, Vocabulary, or Safety Knowledge) based on this response [cite: 2025-12-20, 2025-12-21].
- Provide a short qualitative assessment (sensei_critique) that highlights what the student did well and what needs improvement.

**Output Format (JSON):**
{{
    "grade": <number 1-10>,
    "accuracy_feedback": "<feedback>",
    "grammar_feedback": "<feedback>",
    "weakness_area": "<Grammar|Vocabulary|Safety Knowledge|Other>",
    "sensei_critique": "<Short qualitative assessment of this specific answer>"
}}
"""

        try:
            # SDK Compatibility Fix: Remove generation_config if it causes issues [cite: 2025-12-21]
            # Use simple generate_content call and parse JSON from response
            response_obj = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            
            # Try to parse as JSON, if it fails, extract JSON from text
            try:
                grading_result = json.loads(response_obj.text)
            except json.JSONDecodeError:
                # If response is not pure JSON, try to extract JSON from markdown or text
                import re
                json_match = re.search(r'\{[^{}]*"grade"[^{}]*\}', response_obj.text, re.DOTALL)
                if json_match:
                    grading_result = json.loads(json_match.group())
                else:
                    # Fallback: return default structure
                    grading_result = {"grade": 5, "accuracy_feedback": response_obj.text[:200], "grammar_feedback": "Could not parse JSON response"}
            
            # Granular Tracking: Extract unique vocational words [cite: 2025-07-07]
            question_word_count = self._count_unique_vocational_words(response, transcript_content)
            
            result = {
                "grade": int(grading_result.get("grade", 5)),
                "accuracy_feedback": grading_result.get("accuracy_feedback", "No feedback."),
                "grammar_feedback": grading_result.get("grammar_feedback", "No feedback."),
                "pronunciation_hint": "Pronunciation not assessed in text-only grading.",
                "question_word_count": question_word_count,  # Granular Tracking [cite: 2025-07-07]
                "question_duration": question_duration,  # Granular Tracking [cite: 2025-12-21]
                "sensei_critique": grading_result.get("sensei_critique", "No critique provided."),  # Granular Tracking [cite: 2025-12-21]
                "weakness_area": grading_result.get("weakness_area", "Other"),  # Sensei Logic [cite: 2025-12-20, 2025-12-21]
                "session_id": session_id  # Session Persistence [cite: 2025-12-21]
            }
            
            # Ensure grade is between 1-10
            result["grade"] = max(1, min(10, result["grade"]))
            
            # Trigger Persistence: Save grading result immediately after LLM returns scores [cite: 2025-12-21]
            if lesson_name:
                # Category Tagging: Determine category from track [cite: 2025-12-21]
                category = track if track in ["Academic", "Food/Tech", "Care-giving"] else "Academic"
                
                scores = {
                    "grade": result["grade"],
                    "word_count": len(response.split()) if response else 0,  # Total word count for backward compatibility
                    "question_word_count": question_word_count,  # Unique vocational words [cite: 2025-07-07]
                    "question_duration": question_duration,  # Time elapsed [cite: 2025-12-21]
                    "sensei_critique": result.get("sensei_critique", ""),  # Qualitative assessment [cite: 2025-12-21]
                    "weakness_area": result.get("weakness_area", "Other"),  # Weakness identification [cite: 2025-12-20, 2025-12-21]
                    "accuracy_feedback": result.get("accuracy_feedback", ""),
                    "grammar_feedback": result.get("grammar_feedback", "")
                }
                save_grading_result(lesson_name, scores, session_id=session_id, category=category)

            return result

        except Exception as e:
            return {
                "grade": 5,
                "accuracy_feedback": f"Error during grading: {e}",
                "grammar_feedback": "An error occurred.",
                "pronunciation_hint": "Pronunciation not assessed in text-only grading."
            }
    
    def _count_unique_vocational_words(self, response: str, transcript_content: Optional[str] = None) -> int:
        """
        Count unique vocational words in the response.
        Granular Tracking: Number of unique vocational words in current response only [cite: 2025-07-07]
        """
        if not response:
            return 0
        
        # Extract Japanese words (Kanji, Hiragana, Katakana)
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+'
        japanese_words = set(re.findall(japanese_pattern, response))
        
        # Extract vocational terms from transcript if available
        vocational_terms = set()
        if transcript_content:
            # Look for numbered items or key terms
            # Pattern: "1. 衛生 (Eisei)" or "安全 (Anzen)"
            term_pattern = r'([\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+)\s*\([^)]+\)'
            transcript_terms = re.findall(term_pattern, transcript_content)
            vocational_terms.update(transcript_terms)
        
        # Count unique Japanese words that appear in response
        unique_vocational = japanese_words.intersection(vocational_terms) if vocational_terms else japanese_words
        
        # Also count English vocational terms if they appear in transcript
        if transcript_content:
            # Common vocational terms in English
            english_vocab = ['safety', 'hygiene', 'sanitation', 'cleaning', 'equipment', 'food', 'temperature', 
                           'contamination', 'storage', 'handling', 'uniform', 'training']
            response_lower = response.lower()
            for term in english_vocab:
                if term in response_lower and term in transcript_content.lower():
                    unique_vocational.add(term)
        
        return len(unique_vocational)
    
    def run(self, response: str, candidate_id: Optional[str] = None, track: Optional[str] = "Academic", language: Optional[str] = "en", lesson_name: Optional[str] = None, question_start_time: Optional[float] = None, session_id: Optional[str] = None) -> dict:
        """
        Public method that calls _run() for compatibility.
        The Method: Ensures run method explicitly accepts lesson_name [cite: 2025-12-21]
        Granular Tracking: Accepts question_start_time and session_id [cite: 2025-12-21]
        """
        return self._run(response=response, lesson_name=lesson_name, candidate_id=candidate_id, track=track, language=language, question_start_time=question_start_time, session_id=session_id)


# Storage Logic: Progress persistence function [cite: 2025-12-21]
USER_PROGRESS_FILE = "assets/user_progress.json"

# Database Security: Password for future database archiving connections [cite: 2025-12-21]
# Note: In production, this should be stored in environment variables or a secure secrets manager
DB_ARCHIVE_PASSWORD = os.getenv("DB_ARCHIVE_PASSWORD", "Arm!ta1390")

def save_grading_result(lesson_name: str, scores: dict, session_id: Optional[str] = None, category: Optional[str] = None):
    """
    Saves competency scores to a persistent JSON file with session persistence.
    Session Persistence: Stores under session_id and calculates session totals [cite: 2025-12-21]
    
    Args:
        lesson_name: Name of the lesson (e.g., "2. N5 Kitchen Safety & Hygiene")
        scores: Dictionary containing grade, word_count, question_word_count, question_duration, sensei_critique, etc.
        session_id: Session ID for grouping related questions [cite: 2025-12-21]
        category: Category tag (Academic, Food/Tech, Care-giving) [cite: 2025-12-21]
    """
    # Ensure assets directory exists
    os.makedirs("assets", exist_ok=True)
    
    if os.path.exists(USER_PROGRESS_FILE):
        with open(USER_PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "total_word_count": 0,
            "lesson_history": [],
            "sessions": {}  # Session Persistence: Store sessions by session_id [cite: 2025-12-21]
        }
    
    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid4())
    
    # Initialize session if it doesn't exist
    if "sessions" not in data:
        data["sessions"] = {}
    
    if session_id not in data["sessions"]:
        data["sessions"][session_id] = {
            "session_start": datetime.now().isoformat(),
            "session_total_words": 0,
            "session_total_time": 0.0,
            "questions": []
        }
    
    # Session Persistence: Calculate session totals [cite: 2025-12-21]
    session = data["sessions"][session_id]
    question_word_count = scores.get("question_word_count", 0)
    question_duration = scores.get("question_duration", 0.0) or 0.0
    
    # Update session totals
    session["session_total_words"] += question_word_count
    session["session_total_time"] += question_duration
    
    # Category Tagging: Add category to scores [cite: 2025-12-21]
    if category:
        scores["category"] = category
    
    # Add question to session
    question_entry = {
        "timestamp": datetime.now().isoformat(),
        "lesson": lesson_name,
        "scores": scores
    }
    session["questions"].append(question_entry)
    session["last_updated"] = datetime.now().isoformat()
    
    # Also maintain backward compatibility with lesson_history
    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "lesson": lesson_name,
        "session_id": session_id,  # Link to session
        "category": category,  # Category Tagging [cite: 2025-12-21]
        "scores": scores
    }
    data["lesson_history"].append(new_entry)
    
    # Category Tagging: Only accumulate word count if category matches [cite: 2025-12-21]
    # This prevents Academic scores from leaking into Food/Tech or Care-giving progress bars
    if category == "Academic" or not category:  # Default to Academic if no category specified
        data["total_word_count"] += scores.get("word_count", 0)  # Backward compatibility
    
    with open(USER_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
