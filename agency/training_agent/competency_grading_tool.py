from agency_swarm.tools import BaseTool
from pydantic import Field
import config
from google import genai

class CompetencyGradingTool(BaseTool):
    """
    A tool to grade the competency of a candidate based on a transcript.
    """
    candidate_id: str = Field(..., description="The ID of the candidate.")
    transcript: str = Field(..., description="The transcript to be graded.")
    track: str = Field(..., description="The track for which the competency is being graded.")
    language: str = Field(..., description="The language of the transcript.")

    def _run(self):
        """
        Grades the transcript and returns the score and feedback.
        """
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
        language_name = language_map.get(self.language, "English")

        prompt = f"""You are an expert AI language coach. Your task is to grade the following transcript based on its content, grammar, and overall coherence. The user is in the '{self.track}' track.

        **Transcript:**
        "{self.transcript}"

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
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            
            import json
            grading_result = json.loads(response.text)
            
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
