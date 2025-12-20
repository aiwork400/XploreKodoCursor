"""
Socratic Questioning Tool for TrainingAgent.

Implements Socratic method for caregiving candidates:
- Asks questions (never gives answers)
- Multi-language support (Japanese + Nepali pairs)
- Persists dialogue history to JSONB
- Starts with 'Japanese Bedside Etiquette' (Omotenashi)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import random
from typing import Literal, Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, KnowledgeBase, SessionLocal

# Try to import google-cloud-translate, fallback to placeholder if not available
try:
    from google.cloud import translate_v2 as translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    translate = None

# Try to import google-cloud-texttospeech for TTS
try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    texttospeech = None


class SocraticQuestioningTool(BaseTool):
    """
    Socratic questioning tool for caregiving candidates.
    
    NEVER gives answers - only asks questions that lead candidates to discover
    the correct Japanese caregiving practice.
    
    Features:
    - Multi-language: Questions delivered in Japanese + Nepali pairs
    - Persistence: Saves all interactions to JSONB dialogue_history
    - Topic: Starts with 'Japanese Bedside Etiquette' (Omotenashi)
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    topic: Literal["omotenashi", "knowledge_base", "medication_management", "patient_communication", "hygiene_protocols"] = Field(
        default="knowledge_base", description="Topic for Socratic questioning. Use 'knowledge_base' to pull random concepts from PDF-extracted knowledge base. Default: 'knowledge_base'"
    )
    candidate_response: Optional[str] = Field(
        default=None, description="Candidate's response to the previous question (if continuing a dialogue)"
    )
    start_new_session: bool = Field(
        default=False, description="If True, starts a new Socratic dialogue session (ignores previous dialogue)"
    )

    def _translate_text(self, text: str, target_language: str) -> str:
        """
        Translate text using Google Cloud Translate API.
        
        Uses credentials from .env file (GOOGLE_CLOUD_TRANSLATE_PROJECT_ID and 
        GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH).
        
        Falls back to placeholder if translation service is not available.
        """
        # Check if Google Translate is available
        if not GOOGLE_TRANSLATE_AVAILABLE:
            # Fallback: Return placeholder translation
            if target_language == "ja":
                return f"[Japanese Translation: {text}]"
            elif target_language == "ne":
                return f"[Nepali Translation: {text}]"
            return text
        
        # Check if project ID is configured
        project_id = config.GOOGLE_CLOUD_TRANSLATE_PROJECT_ID
        credentials_path = config.GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH
        
        if not project_id:
            # Fallback: Return placeholder translation
            if target_language == "ja":
                return f"[Japanese Translation: {text}]"
            elif target_language == "ne":
                return f"[Nepali Translation: {text}]"
            return text
        
        try:
            # Initialize translation client
            # Priority: 1) Credentials file path from config, 2) Default google_creds.json, 3) Environment variable, 4) Project ID only
            client = None
            project_root = Path(__file__).parent.parent.parent
            
            # Try credentials path from config
            if credentials_path:
                creds_path = Path(credentials_path)
                if not creds_path.is_absolute():
                    creds_path = project_root / credentials_path
                
                if creds_path.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                    client = translate.Client.from_service_account_json(str(creds_path))
            
            # If no client yet, try default credentials file location
            if client is None:
                default_creds = project_root / "google_creds.json"
                if default_creds.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(default_creds)
                    client = translate.Client.from_service_account_json(str(default_creds))
            
            # If still no client, try environment variable
            if client is None and os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                env_creds = Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
                if env_creds.exists():
                    client = translate.Client()
            
            # Last resort: use project ID only (requires default credentials)
            if client is None:
                client = translate.Client(project=project_id)
            
            # Perform translation
            # Language codes: 'ja' for Japanese, 'ne' for Nepali
            result = client.translate(text, target_language=target_language)
            translated_text = result.get("translatedText", text)
            
            # Ensure we return the translated text, not the original
            if translated_text and translated_text != text:
                return translated_text
            else:
                # If translation failed but no error was raised, return original with warning
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Translation returned same text. Result: {result}")
                return translated_text if translated_text else text
            
        except Exception as e:
            # Log error but don't fail - return placeholder
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Google Translate API error: {e}. Using placeholder translation.")
            
            # Fallback on error
            if target_language == "ja":
                return f"[Japanese Translation: {text}]"
            elif target_language == "ne":
                return f"[Nepali Translation: {text}]"
            return text

    def _generate_audio_files(self, japanese_text: str, nepali_text: str, question_id: str) -> dict:
        """
        Generate MP3 audio files for Japanese and Nepali text using Google Text-to-Speech.
        
        Returns:
            dict with 'japanese' and 'nepali' keys containing relative paths to audio files
        """
        audio_paths = {"japanese": None, "nepali": None}
        
        if not GOOGLE_TTS_AVAILABLE:
            return audio_paths
        
        try:
            # Get project root and create static/audio directory
            project_root = Path(__file__).parent.parent.parent
            audio_dir = project_root / "static" / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize TTS client
            project_id = config.GOOGLE_CLOUD_TRANSLATE_PROJECT_ID
            credentials_path = config.GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH
            
            if not project_id:
                return audio_paths
            
            # Initialize TTS client (same credentials as translation)
            client = None
            if credentials_path:
                creds_path = Path(credentials_path)
                if not creds_path.is_absolute():
                    creds_path = project_root / credentials_path
                if creds_path.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                    client = texttospeech.TextToSpeechClient.from_service_account_json(str(creds_path))
            
            if client is None:
                default_creds = project_root / "google_creds.json"
                if default_creds.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(default_creds)
                    client = texttospeech.TextToSpeechClient.from_service_account_json(str(default_creds))
            
            if client is None and os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                client = texttospeech.TextToSpeechClient()
            
            if client is None:
                return audio_paths
            
            # Generate Japanese audio
            if japanese_text and not japanese_text.startswith("[Japanese Translation:"):
                japanese_audio_path = audio_dir / f"{question_id}_ja.mp3"
                synthesis_input = texttospeech.SynthesisInput(text=japanese_text)
                voice = texttospeech.VoiceSelectionParams(
                    language_code="ja-JP",
                    name="ja-JP-Standard-A",  # Female voice
                    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
                )
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                )
                response = client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
                with open(japanese_audio_path, "wb") as out:
                    out.write(response.audio_content)
                audio_paths["japanese"] = f"static/audio/{question_id}_ja.mp3"
            
            # Generate Nepali audio
            # Note: Google TTS may not support Nepali directly, try hi-IN (Hindi) as fallback
            if nepali_text and not nepali_text.startswith("[Nepali Translation:"):
                nepali_audio_path = audio_dir / f"{question_id}_ne.mp3"
                synthesis_input = texttospeech.SynthesisInput(text=nepali_text)
                
                # Try Nepali first, fallback to Hindi if not available
                try:
                    voice = texttospeech.VoiceSelectionParams(
                        language_code="ne-NP",
                        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
                    )
                except:
                    # Fallback to Hindi (closest available language)
                    voice = texttospeech.VoiceSelectionParams(
                        language_code="hi-IN",
                        name="hi-IN-Standard-A",
                        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
                    )
                
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3
                )
                response = client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
                with open(nepali_audio_path, "wb") as out:
                    out.write(response.audio_content)
                audio_paths["nepali"] = f"static/audio/{question_id}_ne.mp3"
            
        except Exception as e:
            # Log error but don't fail - audio is optional
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Google TTS error: {e}. Audio generation skipped.")
        
        return audio_paths

    def _get_omotenashi_questions(self) -> list[dict]:
        """
        Get Socratic questions for 'Japanese Bedside Etiquette' (Omotenashi).
        
        Returns a list of questions that guide candidates to discover
        the principles of Omotenashi through inquiry.
        """
        return [
            {
                "question_id": "omotenashi_1",
                "question_en": "When you enter a patient's room in Japan, what do you think is the first thing you should do? Why do you think that matters?",
                "learning_objective": "Understanding the importance of greeting and acknowledgment in Japanese caregiving",
                "hint_if_stuck": "Think about respect and making the patient feel seen and valued. In Japan, how do we show respect when entering someone's space?",
            },
            {
                "question_id": "omotenashi_2",
                "question_en": "If a patient seems uncomfortable or in pain, but hasn't said anything, what might that tell you about Japanese communication style? How would you respond?",
                "learning_objective": "Understanding indirect communication and reading non-verbal cues in Japanese culture",
                "hint_if_stuck": "In Japan, people often don't express discomfort directly. What non-verbal signs might indicate pain or discomfort? How can you show you're paying attention?",
            },
            {
                "question_id": "omotenashi_3",
                "question_en": "Before assisting a patient with any task, what should you consider about their dignity and privacy? How does this relate to the concept of 'Omotenashi'?",
                "learning_objective": "Understanding dignity, privacy, and anticipatory service in Omotenashi",
                "hint_if_stuck": "Omotenashi means anticipating needs before they're expressed. How can you prepare the environment to maintain the patient's dignity? What small gestures show respect?",
            },
            {
                "question_id": "omotenashi_4",
                "question_en": "If you need to move something in a patient's room, how would you do it in a way that shows respect for their personal space? What would you say or do?",
                "learning_objective": "Understanding respect for personal space and belongings in Japanese caregiving",
                "hint_if_stuck": "In Japan, personal space and belongings are very important. How would you ask permission? What words or phrases would you use?",
            },
            {
                "question_id": "omotenashi_5",
                "question_en": "When you finish assisting a patient, what is the last thing you should do before leaving? Why is this important in Japanese caregiving?",
                "learning_objective": "Understanding closure and gratitude in Omotenashi",
                "hint_if_stuck": "Think about how you would express gratitude and ensure the patient feels cared for. What would you say? How would you leave the room respectfully?",
            },
        ]

    def _get_random_concept_from_knowledge_base(self, db: Session) -> Optional[dict]:
        """
        Get a random caregiving concept from the knowledge base.
        
        Returns a concept that can be used to generate a Socratic question.
        """
        # Get random concept from knowledge base
        concepts = db.query(KnowledgeBase).filter(
            KnowledgeBase.language == "ja"
        ).all()
        
        if not concepts:
            return None
        
        # Select random concept
        concept = random.choice(concepts)
        
        # Extract key information for Socratic questioning
        # Use first sentence or first 200 chars as the concept focus
        content = concept.concept_content
        first_sentence = content.split('。')[0] if '。' in content else content[:200]
        
        return {
            "concept_title": concept.concept_title,
            "concept_content": first_sentence,
            "full_content": content,
            "source_file": concept.source_file,
            "page_number": concept.page_number,
        }

    def _generate_socratic_question_from_concept(self, concept: dict) -> dict:
        """
        Generate a Socratic question based on a knowledge base concept.
        
        NEVER gives the answer - only asks questions that guide discovery.
        """
        # Generate a Socratic question that helps the candidate discover the concept
        question_en = f"Based on what you know about Japanese caregiving, what do you think '{concept['concept_title']}' means? How would you apply this in a real caregiving situation?"
        
        # If concept content is available, create a more specific question
        if concept.get('concept_content'):
            question_en = f"Let's think about this concept: '{concept['concept_title']}'. What do you think this means in the context of Japanese caregiving? Can you think of a situation where this would be important?"
        
        return {
            "question_id": f"kb_{concept.get('page_number', 0)}_{hash(concept['concept_title']) % 10000}",
            "question_en": question_en,
            "learning_objective": f"Understanding the concept: {concept['concept_title']}",
            "hint_if_stuck": f"Think about how this concept relates to respect, dignity, and proper caregiving practices in Japan. What specific actions or behaviors might this involve?",
            "concept_reference": concept,
        }

    def _get_question_by_topic(self, topic: str, question_index: int = 0, db: Session = None) -> Optional[dict]:
        """
        Get a Socratic question for the specified topic.
        
        If topic is 'knowledge_base' or if knowledge base has content, pull from knowledge base.
        Otherwise, use predefined questions for 'omotenashi'.
        """
        # Try to get from knowledge base first (if available)
        if db:
            concept = self._get_random_concept_from_knowledge_base(db)
            if concept:
                return self._generate_socratic_question_from_concept(concept)
        
        # Fallback to predefined questions
        if topic == "omotenashi":
            questions = self._get_omotenashi_questions()
            if 0 <= question_index < len(questions):
                return questions[question_index]
        return None

    def run(self) -> str:
        """
        Conduct Socratic questioning session.
        
        NEVER gives answers - only asks questions that guide candidates
        to discover correct Japanese caregiving practices.
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

            # Initialize or load dialogue history
            dialogue_history = curriculum.dialogue_history or []
            
            if self.start_new_session:
                dialogue_history = []
                curriculum.dialogue_history = []

            # Determine which question to ask
            current_question_index = len(dialogue_history)
            
            # If candidate provided a response, save it first
            if self.candidate_response:
                if dialogue_history and len(dialogue_history) > 0:
                    # Update the last question with the candidate's response
                    last_entry = dialogue_history[-1]
                    last_entry["candidate_answer"] = self.candidate_response
                    last_entry["answer_timestamp"] = datetime.now(timezone.utc).isoformat()
                else:
                    # Create a new entry for the response (shouldn't happen, but handle gracefully)
                    dialogue_history.append({
                        "candidate_answer": self.candidate_response,
                        "answer_timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            
            # Get the next question for this topic (pass db session for knowledge base lookup)
            question_data = self._get_question_by_topic(self.topic, current_question_index, db)
            
            if not question_data:
                # No questions available (knowledge base might be empty or topic exhausted)
                if self.topic == "knowledge_base":
                    result = f"=== Socratic Questioning: Knowledge Base ===\n"
                    result += f"Candidate: {candidate.full_name} ({self.candidate_id})\n\n"
                    result += "⚠️ **No concepts available in knowledge base.**\n"
                    result += "Please run `python database/extract_pdf_to_knowledge_base.py` to populate the knowledge base.\n"
                    return result
                else:
                    # All questions completed for this topic
                    result = f"=== Socratic Questioning Session Complete ===\n"
                    result += f"Candidate: {candidate.full_name} ({self.candidate_id})\n"
                    result += f"Topic: {self.topic.replace('_', ' ').title()}\n"
                    result += f"Questions Completed: {len(dialogue_history)}\n\n"
                    result += "✅ **Congratulations!** You've completed all questions for this topic.\n"
                    result += "You've discovered the key principles of Japanese caregiving through thoughtful inquiry.\n\n"
                    result += "**Summary of Your Learning Journey:**\n"
                    for i, entry in enumerate(dialogue_history, 1):
                        if "question" in entry:
                            result += f"{i}. {entry.get('question', {}).get('question_en', 'N/A')}\n"
                            if "candidate_answer" in entry:
                                result += f"   Your Answer: {entry['candidate_answer'][:100]}...\n"
                    return result

            # Translate question to Japanese and Nepali
            question_en = question_data["question_en"]
            question_ja = self._translate_text(question_en, "ja")
            question_ne = self._translate_text(question_en, "ne")

            # Generate audio files for Japanese and Nepali questions
            audio_paths = self._generate_audio_files(question_ja, question_ne, question_data["question_id"])

            # Create dialogue entry
            dialogue_entry = {
                "question_id": question_data["question_id"],
                "topic": self.topic,
                "question": {
                    "english": question_en,
                    "japanese": question_ja,
                    "nepali": question_ne,
                },
                "audio_files": audio_paths,  # Store audio file paths
                "learning_objective": question_data["learning_objective"],
                "hint_if_stuck": question_data.get("hint_if_stuck", ""),
                "question_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add to dialogue history
            dialogue_history.append(dialogue_entry)
            curriculum.dialogue_history = dialogue_history

            db.commit()

            # Format response
            topic_display = "Knowledge Base (Random Concept)" if self.topic == "knowledge_base" else self.topic.replace('_', ' ').title()
            result = f"=== Socratic Questioning: {topic_display} ===\n"
            result += f"Candidate: {candidate.full_name} ({self.candidate_id})\n"
            
            # Show concept reference if from knowledge base
            if self.topic == "knowledge_base" and question_data.get("concept_reference"):
                concept_ref = question_data["concept_reference"]
                result += f"📚 Concept from: {Path(concept_ref['source_file']).name} (Page {concept_ref.get('page_number', 'N/A')})\n"
            
            result += f"Question {current_question_index + 1}\n\n"
            
            result += "**🤔 Socratic Question (English):**\n"
            result += f"{question_en}\n\n"
            
            result += "**🇯🇵 Socratic Question (Japanese):**\n"
            result += f"{question_ja}\n\n"
            
            result += "**🇳🇵 Socratic Question (Nepali):**\n"
            result += f"{question_ne}\n\n"
            
            result += "**📚 Learning Objective:**\n"
            result += f"{question_data['learning_objective']}\n\n"
            
            result += "**💡 Remember:**\n"
            result += "- I will NOT give you the answer directly\n"
            result += "- Think deeply about what you know about Japanese caregiving\n"
            result += "- Consider the cultural context and principles of respect\n"
            result += "- If you're stuck, I'll provide a gentle hint, but you must discover the answer yourself\n\n"
            
            result += "**💭 Your Turn:**\n"
            result += "Please provide your answer. I'll guide you with follow-up questions if needed.\n\n"
            
            result += f"✓ Dialogue saved to database (JSONB: dialogue_history)."

            return result

        except Exception as e:
            db.rollback()
            return f"Error in Socratic questioning: {str(e)}"
        finally:
            db.close()

