from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import config
from google import genai
import json

class GradingInput(BaseModel):
    response: str = Field(description="The student's competency statement")
    candidate_id: Optional[str] = Field(default=None, description="The ID of the candidate")
    track: Optional[str] = Field(default="Academic", description="The track for which the competency is being graded")
    language: Optional[str] = Field(default="en", description="The language of the transcript")

class CompetencyGradingTool(BaseTool):
    name: str = "competency_grading_tool"
    description: str = "Evaluates student responses for JLPT and Food Tech mastery"
    args_schema: Type[BaseModel] = GradingInput
    
    # Force Initialization: Print statement to verify it is no longer abstract [cite: 2025-12-21]
    # Tool Attribute Fix: Use self.name instead of global name variable [cite: 2025-12-21]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"Tool initialized: {self.name}")
    
    def _run(self, response: str, **kwargs) -> dict:
        """
        Grades the transcript and returns the score and feedback.
        """
        # Extract optional parameters from kwargs
        candidate_id = kwargs.get('candidate_id', None)
        track = kwargs.get('track', 'Academic')
        language = kwargs.get('language', 'en')
        
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

            return result

        except Exception as e:
            return {
                "grade": 5,
                "accuracy_feedback": f"Error during grading: {e}",
                "grammar_feedback": "An error occurred.",
                "pronunciation_hint": "Pronunciation not assessed in text-only grading."
            }
    
    def run(self, response: str, candidate_id: Optional[str] = None, track: Optional[str] = "Academic", language: Optional[str] = "en") -> dict:
        """
        Public method that calls _run() for compatibility.
        """
        return self._run(response=response, candidate_id=candidate_id, track=track, language=language)
