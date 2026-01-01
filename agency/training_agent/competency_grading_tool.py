from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import config
from google import genai
import json
import os
from datetime import datetime

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

        prompt = f"""You are an expert AI language coach. Your task is to grade the following transcript based on its content, grammar, and overall coherence. The user is in the '{track}' track.

        **Transcript:**
        "{response}"

        **Instructions:**
        - Provide a single overall grade from 1-10.
        - Provide feedback on accuracy and grammar.
        - Keep feedback concise and helpful.

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
