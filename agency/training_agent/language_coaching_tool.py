"""
Language Coaching Tool for TrainingAgent (LanguageCoachAgent).

Implements:
- Speech-to-Text (STT) using Google Cloud Speech-to-Text API
- AI Grading using Gemini 1.5 Flash
- Database updates to curriculum_progress dialogue_history
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, SessionLocal

# Try to import google-cloud-speech
try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False
    speech = None

# Try to import google-genai for Gemini
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class LanguageCoachingTool(BaseTool):
    """
    Language coaching tool that grades candidate audio responses.
    
    Features:
    - Speech-to-Text: Transcribes Japanese/Nepali audio using Google Cloud Speech-to-Text
    - AI Grading: Uses Gemini 1.5 Flash to grade responses (1-10) based on accuracy, grammar, and pronunciation
    - Database Save: Updates curriculum_progress dialogue_history with transcript, grade, and feedback
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    audio_base64: str = Field(..., description="Base64-encoded audio data (WAV, MP3, or M4A format)")
    language_code: str = Field(
        default="ja-JP",
        description="Language code for STT: 'ja-JP' for Japanese, 'ne-NP' for Nepali, or 'auto' for automatic detection"
    )
    question_id: Optional[str] = Field(
        default=None,
        description="Question ID from dialogue_history to associate this response with (optional)"
    )
    expected_answer: Optional[str] = Field(
        default=None,
        description="Expected answer or context for grading (optional, helps with accuracy assessment)"
    )

    def _initialize_speech_client(self):
        """Initialize Google Cloud Speech-to-Text client using credentials."""
        if not GOOGLE_SPEECH_AVAILABLE:
            return None
        
        try:
            project_root = Path(__file__).parent.parent.parent
            client = None
            
            # Priority 1: Check GOOGLE_APPLICATION_CREDENTIALS from config (.env)
            if config.GOOGLE_APPLICATION_CREDENTIALS:
                creds_path = Path(config.GOOGLE_APPLICATION_CREDENTIALS)
                if not creds_path.is_absolute():
                    creds_path = project_root / creds_path
                
                if creds_path.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                    client = speech.SpeechClient.from_service_account_json(str(creds_path))
            
            # Priority 2: Try GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH from config
            if client is None:
                credentials_path = config.GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH
                if credentials_path:
                    creds_path = Path(credentials_path)
                    if not creds_path.is_absolute():
                        creds_path = project_root / credentials_path
                    
                    if creds_path.exists():
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                        client = speech.SpeechClient.from_service_account_json(str(creds_path))
            
            # Priority 3: Try default credentials file location (google_creds.json)
            if client is None:
                default_creds = project_root / "google_creds.json"
                if default_creds.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(default_creds)
                    client = speech.SpeechClient.from_service_account_json(str(default_creds))
            
            # Priority 4: Try environment variable (if already set)
            if client is None and os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                client = speech.SpeechClient()
            
            return client
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize Google Speech client: {e}")
            return None

    def _transcribe_audio(self, audio_content: bytes, language_code: str) -> Optional[str]:
        """
        Transcribe audio using Google Cloud Speech-to-Text.
        
        Returns:
            Transcribed text or None if transcription fails
        """
        client = self._initialize_speech_client()
        if not client:
            return None
        
        try:
            # Try to detect audio format (default to LINEAR16, but support common formats)
            # For web audio (from streamlit-mic-recorder), it's typically WAV/MP3
            # Google Speech-to-Text can auto-detect encoding, so we'll use ENCODING_UNSPECIFIED
            config_obj = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # Auto-detect encoding
                sample_rate_hertz=16000,  # Default sample rate
                language_code=language_code if language_code != "auto" else "ja-JP",
                alternative_language_codes=["ja-JP", "ne-NP", "en-US"] if language_code == "auto" else None,
                enable_automatic_punctuation=True,
                model="latest_long",  # Use latest long model for better accuracy
            )
            
            audio = speech.RecognitionAudio(content=audio_content)
            
            # Perform recognition
            response = client.recognize(config=config_obj, audio=audio)
            
            # Extract transcript
            if response.results:
                transcript = ""
                for result in response.results:
                    transcript += result.alternatives[0].transcript + " "
                return transcript.strip()
            
            return None
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Speech-to-Text error: {e}")
            return None

    def _initialize_gemini_client(self):
        """Initialize Gemini client using Google Cloud API key from .env."""
        if not GEMINI_AVAILABLE:
            return None
        
        try:
            # Get API key from config (loaded from .env file)
            api_key = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("GEMINI_API_KEY not found in .env file. Please set GEMINI_API_KEY in your .env file.")
                return None
            
            # Initialize Gemini client with API key from .env
            # The new SDK requires api_key parameter during client initialization
            client = genai.Client(api_key=api_key)
            return client
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize Gemini client: {e}")
            return None

    def _analyze_cheating_risk(
        self,
        transcript: str,
        expected_answer: str,
        question_type: str
    ) -> dict:
        """
        Analyze transcript for cheating risk indicators.
        
        Flags:
        - Too perfect (exact match with no natural speech patterns)
        - Lack of natural cadence (no pauses, hesitations, corrections)
        - Unusual response patterns
        """
        if not GEMINI_AVAILABLE:
            # Basic heuristic check
            risk_score = 0
            if transcript.strip().lower() == expected_answer.strip().lower():
                risk_score = 30  # Perfect match might indicate cheating
            return {
                "cheating_risk_score": risk_score,
                "risk_level": "Low" if risk_score < 30 else "Medium" if risk_score < 70 else "High",
                "indicators": ["Perfect match detected"] if risk_score >= 30 else []
            }
        
        try:
            api_key = config.GEMINI_API_KEY or ""
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            
            client = genai.Client(api_key=api_key)
            
            prompt = f"""Analyze the following language assessment response for cheating risk indicators.

**Question Type:** {question_type}
**Expected Answer:** {expected_answer}
**Student Response (Transcribed):** {transcript}

**Cheating Risk Indicators to Check:**
1. **Too Perfect**: Is the response exactly matching the expected answer with no natural variations?
2. **Lack of Natural Cadence**: Does the transcript show no pauses, hesitations, self-corrections, or natural speech patterns?
3. **Unusual Patterns**: Does the response seem memorized or read rather than spoken naturally?
4. **Timing Anomalies**: (If available) Was the response given too quickly or too slowly?

**Output Format (JSON only):**
{{
    "cheating_risk_score": <integer 0-100, where 0=no risk, 100=high risk>,
    "risk_level": "<Low/Medium/High>",
    "indicators": ["<list of specific risk indicators found>"],
    "analysis": "<brief explanation of why this score was assigned>"
}}

Provide ONLY the JSON response, no additional text."""
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            return {
                "cheating_risk_score": 0,
                "risk_level": "Unknown",
                "indicators": [f"Analysis error: {str(e)}"],
                "analysis": "Could not analyze cheating risk"
            }

    def _grade_response_with_gemini(
        self,
        transcript: str,
        language: str,
        expected_answer: Optional[str] = None
    ) -> dict:
        """
        Grade candidate response using Gemini 1.5 Flash.
        
        Returns:
            dict with 'grade' (1-10), 'accuracy_feedback', 'grammar_feedback', 'pronunciation_hint'
        """
        client = self._initialize_gemini_client()
        if not client:
            # Fallback: return default grading
            return {
                "grade": 5,
                "accuracy_feedback": "Unable to grade: Gemini API not available",
                "grammar_feedback": "Unable to grade: Gemini API not available",
                "pronunciation_hint": "Please ensure your microphone is working properly.",
            }
        
        try:
            # Build grading prompt
            language_name = "Japanese" if language.startswith("ja") else "Nepali"
            
            # Apply strict grading instruction if XPLOREKODO_STRICT is enabled
            grading_instruction = ""
            if config.GRADING_STANDARD == "XPLOREKODO_STRICT":
                grading_instruction = """
IMPORTANT: Use XPLOREKODO_STRICT grading standard (15% harder than JLPT standard).
- Be more critical of pronunciation accuracy
- Require higher precision in grammar
- Apply stricter scoring thresholds
- Reduce scores by approximately 15% compared to standard JLPT grading
"""
            
            prompt = f"""You are a language coach grading a {language_name} language learning response.

{grading_instruction}

**Candidate's Response (Transcribed):**
{transcript}

**Context:**
This is a response to a Socratic question about Japanese caregiving. The candidate is learning {language_name}.

**Grading Criteria:**
1. **Accuracy (0-10)**: Did they define/answer the question correctly? Did they understand the concept?
2. **Grammar (0-10)**: Is the {language_name} sentence structure correct? Are particles, verb forms, and word order appropriate?
3. **Pronunciation Hint**: Based on common STT (Speech-to-Text) errors, suggest one specific pronunciation tip.

**Expected Answer (if provided):**
{expected_answer if expected_answer else "Not provided - grade based on general {language_name} language proficiency"}

**Instructions:**
- Provide a single overall grade from 1-10 (considering both accuracy and grammar)
- Give specific feedback on accuracy
- Give specific feedback on grammar
- Provide one pronunciation hint based on common STT transcription errors

**Output Format (JSON):**
{{
    "grade": <number 1-10>,
    "accuracy_feedback": "<specific feedback on accuracy>",
    "grammar_feedback": "<specific feedback on grammar>",
    "pronunciation_hint": "<one specific pronunciation tip>"
}}
"""
            
            # Generate response using new SDK syntax
            # Note: Using gemini-2.5-flash (gemini-1.5-flash was deprecated)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            # Parse JSON response - new SDK uses response.text
            response_text = response.text.strip()
            
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Parse JSON
            grading_result = json.loads(response_text)
            
            # Validate and ensure all fields are present
            result = {
                "grade": int(grading_result.get("grade", 5)),
                "accuracy_feedback": grading_result.get("accuracy_feedback", "No feedback provided"),
                "grammar_feedback": grading_result.get("grammar_feedback", "No feedback provided"),
                "pronunciation_hint": grading_result.get("pronunciation_hint", "No hint provided"),
            }
            
            # Ensure grade is between 1-10
            result["grade"] = max(1, min(10, result["grade"]))
            
            # Apply strict grading multiplier if XPLOREKODO_STRICT is enabled
            if config.GRADING_STANDARD == "XPLOREKODO_STRICT":
                # Reduce score by 15% (multiply by 0.85, then round)
                original_grade = result["grade"]
                adjusted_grade = max(1, int(original_grade * 0.85))
                result["grade"] = adjusted_grade
                result["accuracy_feedback"] += f" [XPLOREKODO_STRICT: Score adjusted from {original_grade} to {adjusted_grade}]"
            
            return result
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Gemini grading error: {e}")
            
            # Fallback grading
            return {
                "grade": 5,
                "accuracy_feedback": f"Grading error: {str(e)}",
                "grammar_feedback": "Unable to assess grammar due to grading error",
                "pronunciation_hint": "Please speak clearly and at a moderate pace.",
            }

    def run(self) -> str:
        """
        Process audio, transcribe, grade, and save to database.
        """
        db: Session = SessionLocal()
        try:
            # Verify candidate exists
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Error: Candidate {self.candidate_id} not found."

            # Get or create curriculum progress
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == self.candidate_id
            ).first()

            if not curriculum:
                curriculum = CurriculumProgress(candidate_id=self.candidate_id)
                db.add(curriculum)
                db.flush()

            # Decode audio
            try:
                audio_content = base64.b64decode(self.audio_base64)
            except Exception as e:
                return f"Error: Failed to decode audio data: {str(e)}"

            # Transcribe audio
            transcript = self._transcribe_audio(audio_content, self.language_code)
            
            if not transcript:
                return "Error: Failed to transcribe audio. Please check your audio format and ensure Google Cloud Speech-to-Text is configured."

            # Grade response using Gemini
            grading_result = self._grade_response_with_gemini(
                transcript=transcript,
                language=self.language_code,
                expected_answer=self.expected_answer
            )

            # Update dialogue_history
            dialogue_history = curriculum.dialogue_history or []
            
            # Find the question entry if question_id is provided
            if self.question_id:
                for entry in dialogue_history:
                    if entry.get("question_id") == self.question_id:
                        # Update existing entry with response
                        entry["candidate_answer"] = transcript
                        entry["answer_timestamp"] = datetime.now(timezone.utc).isoformat()
                        entry["grading"] = {
                            "grade": grading_result["grade"],
                            "accuracy_feedback": grading_result["accuracy_feedback"],
                            "grammar_feedback": grading_result["grammar_feedback"],
                            "pronunciation_hint": grading_result["pronunciation_hint"],
                            "grading_timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        break
                else:
                    # Question ID not found, create new entry
                    dialogue_history.append({
                        "question_id": self.question_id,
                        "candidate_answer": transcript,
                        "answer_timestamp": datetime.now(timezone.utc).isoformat(),
                        "grading": {
                            "grade": grading_result["grade"],
                            "accuracy_feedback": grading_result["accuracy_feedback"],
                            "grammar_feedback": grading_result["grammar_feedback"],
                            "pronunciation_hint": grading_result["pronunciation_hint"],
                            "grading_timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    })
            else:
                # No question_id, create standalone entry
                dialogue_history.append({
                    "candidate_answer": transcript,
                    "answer_timestamp": datetime.now(timezone.utc).isoformat(),
                    "grading": {
                        "grade": grading_result["grade"],
                        "accuracy_feedback": grading_result["accuracy_feedback"],
                        "grammar_feedback": grading_result["grammar_feedback"],
                        "pronunciation_hint": grading_result["pronunciation_hint"],
                        "grading_timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                })

            # Save to database
            curriculum.dialogue_history = dialogue_history
            db.commit()

            # Extract word title from question_id or dialogue_history for performance recording
            word_title = None
            category = None
            
            if self.question_id and dialogue_history:
                # Try to find the question entry to get word title
                for entry in dialogue_history:
                    if entry.get("question_id") == self.question_id:
                        # Try to extract word from concept reference
                        if "concept_reference" in entry:
                            word_title = entry["concept_reference"].get("concept_title")
                            category = entry.get("category", entry.get("topic", "knowledge_base"))
                        # Also check if question data has concept info
                        elif "question" in entry:
                            question_data = entry.get("question", {})
                            # Try to extract from question text (look for Japanese characters)
                            import re
                            japanese_match = re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', str(question_data))
                            if japanese_match:
                                word_title = japanese_match.group(0)
                        break
            
            # If word_title still not found, try to extract from expected_answer or transcript
            if not word_title:
                # Try to extract Japanese word from transcript or expected_answer
                import re
                text_to_search = self.expected_answer or transcript or ""
                japanese_match = re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', text_to_search)
                if japanese_match:
                    word_title = japanese_match.group(0)
                    category = "knowledge_base"

            # Record performance in student_performance table (Memory Layer)
            if word_title:
                try:
                    from agency.student_progress_agent.tools import RecordProgress
                    
                    record_tool = RecordProgress(
                        candidate_id=self.candidate_id,
                        word_title=word_title,
                        score=grading_result['grade'],
                        feedback=f"Language coaching session - {grading_result.get('accuracy_feedback', '')[:100]}",
                        accuracy_feedback=grading_result.get('accuracy_feedback'),
                        grammar_feedback=grading_result.get('grammar_feedback'),
                        pronunciation_hint=grading_result.get('pronunciation_hint'),
                        transcript=transcript,
                        language_code=self.language_code,
                        category=category,
                    )
                    record_result = record_tool.run()
                    
                    # Analyze cheating risk
                    cheating_risk_score = 0
                    cheating_risk_level = "Unknown"
                    try:
                        cheating_analysis = self._analyze_cheating_risk(
                            transcript=transcript,
                            expected_answer=self.expected_answer or word_title or "",
                            question_type="Language_Coaching"
                        )
                        cheating_risk_score = cheating_analysis.get("cheating_risk_score", 0)
                        cheating_risk_level = cheating_analysis.get("risk_level", "Unknown")
                        
                        # Log high-risk cases to activity_logs for Admin review
                        if cheating_risk_score >= 70:
                            from utils.activity_logger import ActivityLogger
                            ActivityLogger.log(
                                event_type="Cheating_Risk",
                                severity="Warning",
                                user_id=self.candidate_id,
                                message=f"High cheating risk detected in language coaching: Risk Score {cheating_risk_score}/100",
                                metadata={
                                    "word_title": word_title,
                                    "cheating_risk_score": cheating_risk_score,
                                    "cheating_risk_level": cheating_risk_level,
                                    "indicators": cheating_analysis.get("indicators", []),
                                    "transcript": transcript,
                                    "expected_answer": self.expected_answer or word_title,
                                    "score": grading_result["grade"]
                                }
                            )
                    except Exception:
                        pass  # Don't fail if cheating analysis fails
                    
                    # Log grading activity for admin monitoring
                    try:
                        from utils.activity_logger import ActivityLogger
                        ActivityLogger.log_grading(
                            candidate_id=self.candidate_id,
                            word_title=word_title,
                            score=grading_result["grade"],
                            transcript=transcript,
                            feedback={
                                "accuracy": grading_result.get("accuracy_feedback"),
                                "grammar": grading_result.get("grammar_feedback"),
                                "pronunciation": grading_result.get("pronunciation_hint"),
                                "cheating_risk_score": cheating_risk_score,
                                "cheating_risk_level": cheating_risk_level
                            }
                        )
                    except Exception:
                        pass  # Don't fail if logging fails
                except Exception as e:
                    # Log error but don't fail the main operation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to record performance: {e}")

            # Format response
            result = f"=== Language Coaching Result ===\n"
            result += f"Candidate: {candidate.full_name} ({self.candidate_id})\n\n"
            
            result += "**🎤 Transcribed Response:**\n"
            result += f"{transcript}\n\n"
            
            result += "**📊 AI Grading (Gemini 2.5 Flash):**\n"
            result += f"**Overall Grade: {grading_result['grade']}/10**\n\n"
            
            result += "**✅ Accuracy Feedback:**\n"
            result += f"{grading_result['accuracy_feedback']}\n\n"
            
            result += "**📝 Grammar Feedback:**\n"
            result += f"{grading_result['grammar_feedback']}\n\n"
            
            result += "**🎯 Pronunciation Hint:**\n"
            result += f"{grading_result['pronunciation_hint']}\n\n"
            
            # Add cheating risk warning if detected
            try:
                cheating_analysis = self._analyze_cheating_risk(
                    transcript=transcript,
                    expected_answer=self.expected_answer or word_title or "",
                    question_type="Language_Coaching"
                )
                cheating_risk_score = cheating_analysis.get("cheating_risk_score", 0)
                if cheating_risk_score >= 70:
                    result += f"⚠️ **Cheating Risk Alert:** Risk Score {cheating_risk_score}/100 ({cheating_analysis.get('risk_level', 'High')})\n"
                    result += f"This response has been flagged for Admin review.\n\n"
            except Exception:
                pass
            
            result += f"✓ Results saved to database (dialogue_history)."
            if word_title:
                result += f"\n✓ Performance recorded in Memory Layer (student_performance)."

            return result

        except Exception as e:
            db.rollback()
            return f"Error in language coaching: {str(e)}"
        finally:
            db.close()

