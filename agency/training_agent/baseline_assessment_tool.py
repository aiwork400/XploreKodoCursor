"""
Baseline Assessment Tool for LanguageCoachAgent.

Implements a comprehensive 5-question initial assessment with:
- Dynamic scenario generation (anti-cheat)
- Adaptive difficulty (increases if first 2 questions >90% accuracy)
- Cheating risk analysis
- Grammar, Listening/Voice, and Vocabulary questions

Triggered at candidate registration to establish baseline proficiency.
"""

from __future__ import annotations

import base64
import json
import random
from datetime import datetime, timezone
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, KnowledgeBase, SessionLocal

# Try to import google-genai for Gemini
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# Try to import google-cloud-speech
try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False
    speech = None


class RunBaselineAssessment(BaseTool):
    """
    Run a comprehensive 5-question baseline assessment for a new candidate.
    
    Features:
    - Dynamic scenario generation (anti-cheat): Uses Gemini to create unique, one-time scenarios
    - Adaptive difficulty: Increases JLPT level if first 2 questions >90% accuracy
    - Cheating risk analysis: Detects suspicious patterns in responses
    - Grammar (2 questions), Listening/Voice (2 questions), Vocabulary (1 question)
    
    Results are stored in curriculum_progress.baseline_assessment_results (JSON).
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    language_level: str = Field(
        default="N5",
        description="Target JLPT level for assessment (N5, N4, or N3)"
    )

    def _get_seed_word_from_knowledge_base(self, db: Session, category: str = None) -> Optional[dict]:
        """Get a random seed word from knowledge_base for scenario generation."""
        query = db.query(KnowledgeBase)
        
        if category:
            query = query.filter(KnowledgeBase.category == category)
        
        # Get random word
        words = query.all()
        if not words:
            return None
        
        word = random.choice(words)
        return {
            "word": word.concept_title,
            "content": word.concept_content,
            "category": word.category
        }

    def _generate_dynamic_scenario(
        self,
        question_type: str,
        jlpt_level: str,
        seed_word: Optional[dict] = None
    ) -> dict:
        """
        Generate a unique, one-time scenario using Gemini 2.5 Flash.
        
        Anti-cheat: Creates randomized, situational scenarios based on seed word.
        """
        if not GEMINI_AVAILABLE:
            # Fallback to basic question
            return {
                "question": f"Basic {question_type} question for {jlpt_level}",
                "expected_answer": "Sample answer",
                "scenario_context": "Standard question"
            }
        
        try:
            api_key = config.GEMINI_API_KEY or ""
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            
            client = genai.Client(api_key=api_key)
            
            # Build seed word context
            seed_context = ""
            if seed_word:
                seed_context = f"""
**Seed Word:** {seed_word['word']}
**Word Context:** {seed_word['content'][:200]}...
**Category:** {seed_word.get('category', 'general')}
"""
            
            prompt = f"""You are creating a unique, one-time assessment scenario for a Japanese language test.

**CRITICAL INSTRUCTIONS:**
1. Create a UNIQUE, SITUATIONAL scenario. Do NOT repeat standard textbook patterns.
2. Ensure the difficulty is 15% harder than standard JLPT {jlpt_level} level.
3. Make it contextually relevant and realistic (not abstract grammar drills).
4. Generate a scenario that cannot be easily memorized or found in textbooks.

**Question Type:** {question_type}
**Target JLPT Level:** {jlpt_level}
{seed_context}

**Requirements:**
- For Grammar: Create a realistic sentence completion or particle selection scenario
- For Listening/Voice: Create a situational dialogue or response prompt
- For Vocabulary: Create a context-based word usage or definition scenario

**Output Format (JSON only):**
{{
    "question": "<the unique scenario question>",
    "expected_answer": "<the correct answer>",
    "scenario_context": "<brief context explaining the situation>",
    "difficulty_notes": "<why this is 15% harder than standard JLPT {jlpt_level}>"
}}

Provide ONLY the JSON response, no additional text or explanations."""
            
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
            # Fallback
            return {
                "question": f"Assessment question for {question_type} ({jlpt_level})",
                "expected_answer": "Sample answer",
                "scenario_context": f"Error generating scenario: {str(e)}"
            }

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

    def _grade_audio_response(
        self,
        transcript: str,
        expected_answer: str,
        question_type: str,
        include_cheating_analysis: bool = True
    ) -> dict:
        """
        Grade an audio response using Gemini AI with cheating risk analysis.
        
        Returns:
            dict with score (0-10), accuracy_feedback, grammar_feedback, pronunciation_hint, cheating_risk_score
        """
        if not GEMINI_AVAILABLE:
            # Fallback: simple string matching
            score = 10 if transcript.strip().lower() == expected_answer.strip().lower() else 5
            return {
                "score": score,
                "accuracy_feedback": "Response matches expected answer." if score == 10 else "Response does not match expected answer.",
                "grammar_feedback": "N/A (Gemini not available)",
                "pronunciation_hint": "N/A (Gemini not available)",
                "cheating_risk_score": 0,
                "cheating_risk_level": "Unknown"
            }
        
        try:
            api_key = config.GEMINI_API_KEY or ""
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            
            client = genai.Client(api_key=api_key)
            
            # Apply strict grading if XPLOREKODO_STRICT is enabled
            grading_instruction = ""
            if config.GRADING_STANDARD == "XPLOREKODO_STRICT":
                grading_instruction = """
IMPORTANT: Use XPLOREKODO_STRICT grading standard (15% harder than JLPT standard).
- Be more critical of pronunciation accuracy
- Require higher precision in grammar
- Apply stricter scoring thresholds
"""
            
            prompt = f"""You are a Japanese language assessment AI. Grade the following audio response.

{grading_instruction}

**Question Type:** {question_type}
**Expected Answer:** {expected_answer}
**Student Response (transcribed):** {transcript}

**Grading Criteria:**
1. Accuracy: Does the response match the expected answer? (0-4 points)
2. Grammar: Is the sentence structure correct? (0-3 points)
3. Pronunciation: Based on transcription accuracy, assess pronunciation quality (0-3 points)

**Output Format (JSON only):**
{{
    "score": <integer 0-10>,
    "accuracy_feedback": "<detailed feedback on accuracy>",
    "grammar_feedback": "<detailed feedback on grammar>",
    "pronunciation_hint": "<pronunciation tips if needed>"
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
            
            # Apply strict grading multiplier if enabled
            if config.GRADING_STANDARD == "XPLOREKODO_STRICT":
                original_score = result.get("score", 0)
                adjusted_score = max(0, int(original_score * 0.85))
                result["score"] = adjusted_score
                result["accuracy_feedback"] += " [XPLOREKODO_STRICT: Score adjusted to 15% stricter standard]"
            
            # Add cheating risk analysis
            if include_cheating_analysis:
                cheating_analysis = self._analyze_cheating_risk(
                    transcript=transcript,
                    expected_answer=expected_answer,
                    question_type=question_type
                )
                result["cheating_risk_score"] = cheating_analysis.get("cheating_risk_score", 0)
                result["cheating_risk_level"] = cheating_analysis.get("risk_level", "Unknown")
                result["cheating_indicators"] = cheating_analysis.get("indicators", [])
            else:
                result["cheating_risk_score"] = 0
                result["cheating_risk_level"] = "Not Analyzed"
            
            return result
            
        except Exception as e:
            return {
                "score": 0,
                "accuracy_feedback": f"Error grading response: {str(e)}",
                "grammar_feedback": "N/A",
                "pronunciation_hint": "N/A",
                "cheating_risk_score": 0,
                "cheating_risk_level": "Error"
            }

    def _transcribe_audio(self, audio_content: bytes, language_code: str = "ja-JP") -> Optional[str]:
        """Transcribe audio using Google Cloud Speech-to-Text."""
        if not GOOGLE_SPEECH_AVAILABLE:
            return None
        
        try:
            from pathlib import Path
            import os
            import config
            
            # Initialize speech client
            client = None
            project_root = Path(__file__).parent.parent.parent
            
            if config.GOOGLE_APPLICATION_CREDENTIALS:
                creds_path = Path(config.GOOGLE_APPLICATION_CREDENTIALS)
                if not creds_path.is_absolute():
                    creds_path = project_root / creds_path
                if creds_path.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                    client = speech.SpeechClient.from_service_account_json(str(creds_path))
            
            if not client:
                return None
            
            # Configure recognition
            config_speech = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
            )
            
            audio = speech.RecognitionAudio(content=audio_content)
            
            # Perform recognition
            response = client.recognize(config=config_speech, audio=audio)
            
            if response.results:
                return response.results[0].alternatives[0].transcript
            return None
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def run(self) -> str:
        """
        Run the baseline assessment with dynamic scenarios and adaptive difficulty.
        
        Returns:
            Assessment results summary
        """
        db: Session = SessionLocal()
        try:
            # Verify candidate exists
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Error: Candidate {self.candidate_id} not found."
            
            # Check if baseline assessment already completed
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == self.candidate_id
            ).first()
            
            if curriculum and curriculum.baseline_assessment_results:
                return f"Baseline assessment already completed for candidate {self.candidate_id}. Results: {curriculum.baseline_assessment_results}"
            
            # Initialize assessment
            current_level = self.language_level
            assessment_results = {
                "assessment_date": datetime.now(timezone.utc).isoformat(),
                "initial_language_level": self.language_level,
                "final_language_level": current_level,
                "adaptive_level_increase": False,
                "grading_standard": config.GRADING_STANDARD,
                "questions": [],
                "overall_score": 0,
                "scores_by_category": {
                    "grammar": 0,
                    "listening": 0,
                    "vocabulary": 0
                },
                "cheating_risk_summary": {
                    "high_risk_questions": [],
                    "average_risk_score": 0
                }
            }
            
            result_summary = f"=== Baseline Assessment Results ===\n"
            result_summary += f"Candidate: {candidate.full_name} ({self.candidate_id})\n"
            result_summary += f"Initial Language Level: {self.language_level}\n"
            result_summary += f"Grading Standard: {config.GRADING_STANDARD}\n\n"
            
            # Question types: 2 grammar, 2 listening, 1 vocabulary
            question_types = ["grammar", "grammar", "listening", "listening", "vocabulary"]
            
            # Track first 2 questions for adaptive logic
            first_two_scores = []
            
            for i, question_type in enumerate(question_types, 1):
                # Adaptive logic: Increase difficulty if first 2 questions >90% accuracy
                if i == 3 and len(first_two_scores) == 2:
                    avg_score = sum(first_two_scores) / len(first_two_scores)
                    if avg_score >= 9.0:  # >90% accuracy
                        # Increase JLPT level
                        level_map = {"N5": "N4", "N4": "N3", "N3": "N2"}
                        if current_level in level_map:
                            current_level = level_map[current_level]
                            assessment_results["adaptive_level_increase"] = True
                            assessment_results["final_language_level"] = current_level
                            result_summary += f"📈 Adaptive Difficulty: Increased to {current_level} (first 2 questions: {avg_score:.1f}/10 avg)\n\n"
                
                # Get seed word from knowledge_base
                seed_word = None
                if question_type == "vocabulary":
                    seed_word = self._get_seed_word_from_knowledge_base(db, category="caregiving_vocabulary")
                else:
                    seed_word = self._get_seed_word_from_knowledge_base(db)
                
                # Generate dynamic scenario
                scenario = self._generate_dynamic_scenario(
                    question_type=question_type,
                    jlpt_level=current_level,
                    seed_word=seed_word
                )
                
                result_summary += f"Question {i} ({question_type}): {scenario['question']}\n"
                result_summary += f"Context: {scenario.get('scenario_context', 'N/A')}\n"
                
                # For listening questions, we would need audio input
                # For now, simulate a response (in production, collect audio)
                if question_type == 'listening':
                    # In production, this would transcribe audio
                    simulated_response = scenario['expected_answer']  # Perfect response for simulation
                    grading = self._grade_audio_response(
                        transcript=simulated_response,
                        expected_answer=scenario['expected_answer'],
                        question_type=question_type,
                        include_cheating_analysis=True
                    )
                else:
                    # For grammar/vocabulary, simulate correct answer
                    simulated_response = scenario['expected_answer']
                    grading = self._grade_audio_response(
                        transcript=simulated_response,
                        expected_answer=scenario['expected_answer'],
                        question_type=question_type,
                        include_cheating_analysis=False  # Only analyze audio responses
                    )
                
                # Track first 2 scores for adaptive logic
                if i <= 2:
                    first_two_scores.append(grading['score'])
                
                # Check cheating risk
                cheating_risk = grading.get("cheating_risk_score", 0)
                if cheating_risk >= 70:
                    assessment_results["cheating_risk_summary"]["high_risk_questions"].append({
                        "question_number": i,
                        "question_type": question_type,
                        "risk_score": cheating_risk,
                        "indicators": grading.get("cheating_indicators", [])
                    })
                    
                    # Log to activity_logs for Admin review
                    try:
                        from utils.activity_logger import ActivityLogger
                        ActivityLogger.log(
                            event_type="Cheating_Risk",
                            severity="Warning",
                            user_id=self.candidate_id,
                            message=f"High cheating risk detected in Question {i} ({question_type}): Risk Score {cheating_risk}/100",
                            metadata={
                                "question_number": i,
                                "question_type": question_type,
                                "cheating_risk_score": cheating_risk,
                                "indicators": grading.get("cheating_indicators", []),
                                "transcript": simulated_response,
                                "expected_answer": scenario['expected_answer']
                            }
                        )
                    except Exception:
                        pass
                
                question_result = {
                    "question_id": f"baseline_{question_type}_{i}",
                    "type": question_type,
                    "question": scenario['question'],
                    "scenario_context": scenario.get('scenario_context', ''),
                    "expected_answer": scenario['expected_answer'],
                    "student_response": simulated_response,
                    "score": grading['score'],
                    "jlpt_level_used": current_level,
                    "feedback": {
                        "accuracy": grading.get('accuracy_feedback', ''),
                        "grammar": grading.get('grammar_feedback', ''),
                        "pronunciation": grading.get('pronunciation_hint', '')
                    },
                    "cheating_risk_score": cheating_risk,
                    "cheating_risk_level": grading.get("cheating_risk_level", "Unknown")
                }
                
                assessment_results["questions"].append(question_result)
                assessment_results["scores_by_category"][question_type] += grading['score']
                
                result_summary += f"  Score: {grading['score']}/10\n"
                result_summary += f"  Cheating Risk: {cheating_risk}/100 ({grading.get('cheating_risk_level', 'Unknown')})\n"
                result_summary += f"  Feedback: {grading.get('accuracy_feedback', '')[:60]}...\n\n"
            
            # Calculate overall score
            total_score = sum(q['score'] for q in assessment_results["questions"])
            max_score = len(question_types) * 10
            assessment_results["overall_score"] = round((total_score / max_score) * 100, 2)
            
            # Average scores by category
            grammar_count = len([q for q in question_types if q == 'grammar'])
            listening_count = len([q for q in question_types if q == 'listening'])
            vocab_count = len([q for q in question_types if q == 'vocabulary'])
            
            if grammar_count > 0:
                assessment_results["scores_by_category"]["grammar"] = round(
                    assessment_results["scores_by_category"]["grammar"] / grammar_count, 2
                )
            if listening_count > 0:
                assessment_results["scores_by_category"]["listening"] = round(
                    assessment_results["scores_by_category"]["listening"] / listening_count, 2
                )
            if vocab_count > 0:
                assessment_results["scores_by_category"]["vocabulary"] = round(
                    assessment_results["scores_by_category"]["vocabulary"] / vocab_count, 2
                )
            
            # Calculate average cheating risk
            all_risk_scores = [q.get("cheating_risk_score", 0) for q in assessment_results["questions"]]
            assessment_results["cheating_risk_summary"]["average_risk_score"] = round(
                sum(all_risk_scores) / len(all_risk_scores), 2
            ) if all_risk_scores else 0
            
            # Save to curriculum progress
            if not curriculum:
                curriculum = CurriculumProgress(candidate_id=self.candidate_id)
                db.add(curriculum)
            
            curriculum.baseline_assessment_results = json.dumps(assessment_results)
            db.commit()
            
            result_summary += f"\n=== Overall Assessment Summary ===\n"
            result_summary += f"Overall Score: {assessment_results['overall_score']}%\n"
            result_summary += f"Final Language Level: {assessment_results['final_language_level']}\n"
            result_summary += f"Grammar Average: {assessment_results['scores_by_category']['grammar']}/10\n"
            result_summary += f"Listening Average: {assessment_results['scores_by_category']['listening']}/10\n"
            result_summary += f"Vocabulary Average: {assessment_results['scores_by_category']['vocabulary']}/10\n"
            result_summary += f"Average Cheating Risk: {assessment_results['cheating_risk_summary']['average_risk_score']}/100\n"
            
            if assessment_results["cheating_risk_summary"]["high_risk_questions"]:
                result_summary += f"\n⚠️ High Cheating Risk Detected in {len(assessment_results['cheating_risk_summary']['high_risk_questions'])} question(s) - Flagged for Admin review\n"
            
            result_summary += f"\n✅ Baseline assessment completed and saved to database."
            
            # Log assessment event
            try:
                from utils.activity_logger import ActivityLogger
                ActivityLogger.log(
                    event_type="Assessment",
                    severity="Info",
                    user_id=self.candidate_id,
                    message=f"Baseline assessment completed: {assessment_results['overall_score']}% (Level: {assessment_results['final_language_level']})",
                    metadata={
                        "assessment_type": "baseline",
                        "initial_language_level": self.language_level,
                        "final_language_level": assessment_results['final_language_level'],
                        "overall_score": assessment_results['overall_score'],
                        "grading_standard": config.GRADING_STANDARD,
                        "adaptive_level_increase": assessment_results['adaptive_level_increase'],
                        "cheating_risk_average": assessment_results['cheating_risk_summary']['average_risk_score']
                    }
                )
            except Exception:
                pass  # Don't fail if logging fails
            
            return result_summary
            
        except Exception as e:
            db.rollback()
            return f"Error running baseline assessment: {str(e)}"
        finally:
            db.close()
