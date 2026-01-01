from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import config
from google import genai
import json
import os
from datetime import datetime
from pathlib import Path

class GradingInput(BaseModel):
    response: str = Field(description="The student's competency statement")
    candidate_id: Optional[str] = Field(default=None, description="The ID of the candidate")
    track: Optional[str] = Field(default="Academic", description="The track for which the competency is being graded")
    language: Optional[str] = Field(default="en", description="The language of the transcript")
    lesson_name: Optional[str] = Field(default=None, description="The name of the lesson being graded")

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
        Grades the transcript and returns the score and feedback.
        
        The Method: Explicitly accepts lesson_name as an argument [cite: 2025-12-21]
        """
        # Extract optional parameters from kwargs
        candidate_id = kwargs.get('candidate_id', None)
        track = kwargs.get('track', 'Academic')
        language = kwargs.get('language', 'en')
        # lesson_name is now an explicit parameter, but also check kwargs for backward compatibility
        if lesson_name is None:
            lesson_name = kwargs.get('lesson_name', None)
        
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

**Output Format (JSON):**
{{
    "grade": <number 1-10>,
    "accuracy_feedback": "<feedback>",
    "grammar_feedback": "<feedback>"
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
            
            result = {
                "grade": int(grading_result.get("grade", 5)),
                "accuracy_feedback": grading_result.get("accuracy_feedback", "No feedback."),
                "grammar_feedback": grading_result.get("grammar_feedback", "No feedback."),
                "pronunciation_hint": "Pronunciation not assessed in text-only grading."
            }
            
            # Ensure grade is between 1-10
            result["grade"] = max(1, min(10, result["grade"]))
            
            # Trigger Persistence: Save grading result immediately after LLM returns scores [cite: 2025-12-21]
            if lesson_name:
                # Calculate word count from response
                word_count = len(response.split()) if response else 0
                scores = {
                    "grade": result["grade"],
                    "word_count": word_count,
                    "accuracy_feedback": result.get("accuracy_feedback", ""),
                    "grammar_feedback": result.get("grammar_feedback", "")
                }
                save_grading_result(lesson_name, scores)

            return result

        except Exception as e:
            return {
                "grade": 5,
                "accuracy_feedback": f"Error during grading: {e}",
                "grammar_feedback": "An error occurred.",
                "pronunciation_hint": "Pronunciation not assessed in text-only grading."
            }
    
    def run(self, response: str, candidate_id: Optional[str] = None, track: Optional[str] = "Academic", language: Optional[str] = "en", lesson_name: Optional[str] = None) -> dict:
        """
        Public method that calls _run() for compatibility.
        The Method: Ensures run method explicitly accepts lesson_name [cite: 2025-12-21]
        """
        return self._run(response=response, lesson_name=lesson_name, candidate_id=candidate_id, track=track, language=language)


# Storage Logic: Progress persistence function [cite: 2025-12-21]
USER_PROGRESS_FILE = "assets/user_progress.json"

def save_grading_result(lesson_name: str, scores: dict):
    """
    Saves competency scores to a persistent JSON file.
    
    Args:
        lesson_name: Name of the lesson (e.g., "2. N5 Kitchen Safety & Hygiene")
        scores: Dictionary containing grade, word_count, and feedback
    """
    # Ensure assets directory exists
    os.makedirs("assets", exist_ok=True)
    
    if os.path.exists(USER_PROGRESS_FILE):
        with open(USER_PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"total_word_count": 0, "lesson_history": []}

    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "lesson": lesson_name,
        "scores": scores
    }
    data["lesson_history"].append(new_entry)
    data["total_word_count"] += scores.get("word_count", 0)
    
    with open(USER_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
