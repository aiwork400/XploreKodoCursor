"""
XploreKodo Agency API Layer (FastAPI)

Exposes REST endpoints for:
- POST /start-lesson: Triggers TrainingAgent to generate VirtualInstructorTool script
- POST /process-voice: Processes base64 audio (Nepali) -> Japanese text/audio
- GET /candidate-wisdom: Fetches OperationsAgent wisdom report for a candidate

All endpoints verify Phase 2 eligibility from PostgreSQL database.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from database.db_manager import Candidate, SessionLocal

# Import Phase 2 tools (may raise error if PHASE_2_ENABLED is False)
try:
    from mvp_v1.training.voice_to_voice import VoiceToVoiceTranslator
except RuntimeError:
    VoiceToVoiceTranslator = None  # Will be None if Phase 2 is disabled

from agency.training_agent.tools import VirtualInstructorTool
from agency.training_agent.language_coaching_tool import LanguageCoachingTool
from agency.operations_agent.tools import GenerateWisdomReport

# Initialize FastAPI app
app = FastAPI(
    title="XploreKodo Agency API",
    description="API layer for XploreKodo multi-agent system",
    version="1.0.0",
)


# Request/Response Models
class StartLessonRequest(BaseModel):
    candidate_id: str
    module_type: str  # "jlpt" or "kaigo"
    jlpt_level: str | None = None  # "N5", "N4", "N3" (if module_type="jlpt")
    kaigo_module: str | None = None  # "kaigo_basics", "communication_skills", "physical_care" (if module_type="kaigo")


class ProcessVoiceRequest(BaseModel):
    candidate_id: str
    audio_base64: str  # Base64-encoded audio string (Nepali)
    tts_voice: str = "alloy"  # "alloy" or "shimmer"


class ProcessVoiceResponse(BaseModel):
    success: bool
    audio_output_path: str | None = None
    transcribed_text: str | None = None
    translated_text: str | None = None
    message: str


class CandidateWisdomResponse(BaseModel):
    success: bool
    report: str | None = None
    message: str


class LanguageCoachingRequest(BaseModel):
    candidate_id: str
    audio_base64: str  # Base64-encoded audio data
    language_code: str = "ja-JP"  # "ja-JP" for Japanese, "ne-NP" for Nepali, or "auto"
    question_id: str | None = None  # Optional: question ID from dialogue_history
    expected_answer: str | None = None  # Optional: expected answer for grading context


class LanguageCoachingResponse(BaseModel):
    success: bool
    transcript: str | None = None
    grade: int | None = None  # 1-10
    accuracy_feedback: str | None = None
    grammar_feedback: str | None = None
    pronunciation_hint: str | None = None
    message: str


# Helper function to check Phase 2 eligibility
def check_phase_2_eligibility(candidate_id: str) -> tuple[bool, str]:
    """
    Check if candidate is eligible for Phase 2 features.

    Returns:
        (is_eligible: bool, message: str)
    """
    if not config.PHASE_2_ENABLED:
        return False, "Phase 2 features are not enabled. Set PHASE_2_ENABLED=True in .env"

    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not candidate:
            return False, f"Candidate {candidate_id} not found in database."

        # Check if candidate is travel-ready (basic eligibility)
        if not candidate.travel_ready:
            return False, f"Candidate {candidate_id} is not travel-ready. Complete all requirements first."

        return True, "Candidate is eligible for Phase 2 features."
    except Exception as e:
        return False, f"Database error: {str(e)}"
    finally:
        db.close()


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "XploreKodo Agency API",
        "version": "1.0.0",
        "phase_2_enabled": config.PHASE_2_ENABLED,
        "endpoints": {
            "POST /start-lesson": "Generate VirtualInstructorTool lesson script",
            "POST /process-voice": "Process Nepali audio -> Japanese text/audio",
            "GET /candidate-wisdom": "Get wisdom report for a candidate",
        },
    }


@app.post("/start-lesson", response_model=dict)
async def start_lesson(request: StartLessonRequest):
    """
    Trigger TrainingAgent to generate a VirtualInstructorTool script.

    Verifies Phase 2 eligibility before generating the lesson script.
    """
    # Check Phase 2 eligibility
    is_eligible, message = check_phase_2_eligibility(request.candidate_id)
    if not is_eligible:
        raise HTTPException(status_code=403, detail=message)

    try:
        # Create VirtualInstructorTool instance
        tool = VirtualInstructorTool(
            candidate_id=request.candidate_id,
            module_type=request.module_type,
            jlpt_level=request.jlpt_level,
            kaigo_module=request.kaigo_module,
        )

        # Generate lesson script
        script_result = tool.run()

        return {
            "success": True,
            "candidate_id": request.candidate_id,
            "module_type": request.module_type,
            "lesson_script": script_result,
            "message": "Lesson script generated successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating lesson script: {str(e)}")


@app.post("/process-voice", response_model=ProcessVoiceResponse)
async def process_voice(request: ProcessVoiceRequest):
    """
    Process base64 audio string (Nepali) -> Japanese text/audio.

    Uses VoiceToVoiceTranslator with OpenAI Whisper, GPT-4o, and TTS.
    Verifies Phase 2 eligibility before processing.
    """
    # Check Phase 2 eligibility
    is_eligible, message = check_phase_2_eligibility(request.candidate_id)
    if not is_eligible:
        return ProcessVoiceResponse(
            success=False,
            message=message,
        )

    try:
        if VoiceToVoiceTranslator is None:
            return ProcessVoiceResponse(
                success=False,
                message="VoiceToVoiceTranslator is not available. Phase 2 must be enabled.",
            )

        # Create VoiceToVoiceTranslator instance
        translator = VoiceToVoiceTranslator(
            audio_base64=request.audio_base64,
            source_language="Nepali",
            target_language="Japanese",
            tts_voice=request.tts_voice,
        )

        # Process voice-to-voice translation
        result = translator.run()

        # Parse result to extract paths and text
        # The result is a formatted string, so we'll extract key information
        audio_output_path = None
        transcribed_text = None
        translated_text = None

        # Extract audio path from result
        for line in result.split("\n"):
            if "Audio Output Path:" in line:
                audio_output_path = line.split("Audio Output Path:")[-1].strip()
                break

        # Extract transcribed text (look for line with "Transcribed Nepali audio:")
        for line in result.split("\n"):
            if "Transcribed Nepali audio:" in line:
                # Extract text between quotes
                if '"' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        transcribed_text = parts[1]
                break

        # Extract translated text (look for line with "Translated to Polite Japanese:")
        for line in result.split("\n"):
            if "Translated to Polite Japanese:" in line:
                # Extract text between quotes
                if '"' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        translated_text = parts[1]
                break

        return ProcessVoiceResponse(
            success=True,
            audio_output_path=audio_output_path,
            transcribed_text=transcribed_text,
            translated_text=translated_text,
            message="Voice-to-voice translation completed successfully.",
        )
    except Exception as e:
        return ProcessVoiceResponse(
            success=False,
            message=f"Error processing voice: {str(e)}",
        )


@app.get("/candidate-wisdom/{candidate_id}", response_model=CandidateWisdomResponse)
async def get_candidate_wisdom(candidate_id: str):
    """
    Fetch OperationsAgent wisdom report for a specific candidate.

    Verifies Phase 2 eligibility before generating the report.
    """
    # Check Phase 2 eligibility
    is_eligible, message = check_phase_2_eligibility(candidate_id)
    if not is_eligible:
        return CandidateWisdomResponse(
            success=False,
            message=message,
        )

    try:
        # Create GenerateWisdomReport tool instance
        tool = GenerateWisdomReport(
            date=None,  # Use today's date
            include_token_metrics=True,
        )

        # Generate wisdom report
        report_result = tool.run()

        # Extract report content (the tool returns a formatted string)
        # The report is saved to file, but we also return it in the response
        return CandidateWisdomResponse(
            success=True,
            report=report_result,
            message="Wisdom report generated successfully.",
        )
    except Exception as e:
        return CandidateWisdomResponse(
            success=False,
            message=f"Error generating wisdom report: {str(e)}",
        )


@app.post("/language-coaching", response_model=LanguageCoachingResponse)
async def language_coaching(request: LanguageCoachingRequest):
    """
    Process audio recording, transcribe, grade with Gemini, and save to database.
    
    Uses Google Cloud Speech-to-Text for transcription and Gemini 1.5 Flash for grading.
    """
    # Check Phase 2 eligibility
    is_eligible, message = check_phase_2_eligibility(request.candidate_id)
    if not is_eligible:
        return LanguageCoachingResponse(
            success=False,
            message=message,
        )

    try:
        # Create LanguageCoachingTool instance
        tool = LanguageCoachingTool(
            candidate_id=request.candidate_id,
            audio_base64=request.audio_base64,
            language_code=request.language_code,
            question_id=request.question_id,
            expected_answer=request.expected_answer,
        )

        # Process audio, transcribe, and grade
        result = tool.run()

        # Parse result to extract information
        # The result is a formatted string, so we'll extract key information
        transcript = None
        grade = None
        accuracy_feedback = None
        grammar_feedback = None
        pronunciation_hint = None

        # Extract transcript
        for line in result.split("\n"):
            if "**🎤 Transcribed Response:**" in line or "Transcribed Response:" in line:
                # Get next line
                lines = result.split("\n")
                idx = result.split("\n").index(line)
                if idx + 1 < len(lines):
                    transcript = lines[idx + 1].strip()
                break

        # Extract grade
        for line in result.split("\n"):
            if "**Overall Grade:" in line or "Overall Grade:" in line:
                # Extract number from line like "**Overall Grade: 8/10**"
                import re
                match = re.search(r'(\d+)/10', line)
                if match:
                    grade = int(match.group(1))
                break

        # Extract feedback sections
        lines = result.split("\n")
        for i, line in enumerate(lines):
            if "**✅ Accuracy Feedback:**" in line or "Accuracy Feedback:" in line:
                if i + 1 < len(lines):
                    accuracy_feedback = lines[i + 1].strip()
            elif "**📝 Grammar Feedback:**" in line or "Grammar Feedback:" in line:
                if i + 1 < len(lines):
                    grammar_feedback = lines[i + 1].strip()
            elif "**🎯 Pronunciation Hint:**" in line or "Pronunciation Hint:" in line:
                if i + 1 < len(lines):
                    pronunciation_hint = lines[i + 1].strip()

        return LanguageCoachingResponse(
            success=True,
            transcript=transcript,
            grade=grade,
            accuracy_feedback=accuracy_feedback,
            grammar_feedback=grammar_feedback,
            pronunciation_hint=pronunciation_hint,
            message="Language coaching completed successfully.",
        )
    except Exception as e:
        return LanguageCoachingResponse(
            success=False,
            message=f"Error in language coaching: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

