"""
Video-Triggered Socratic Assessment Tool

Handles Socratic Assessment triggered from Video Hub with:
- Session Snapshot (track, topic, video_timestamp)
- Evaluation Rubric (Acceptable, Partially Acceptable, Non-Acceptable)
- Feedback Loop (prevents video resumption until feedback acknowledged)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal, Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, SessionLocal
from models.curriculum import Syllabus

# Try to import Gemini for evaluation
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class VideoSocraticAssessmentTool(BaseTool):
    """
    Video-triggered Socratic Assessment with evaluation rubric.
    
    Features:
    - Session Snapshot: Receives track, topic, and video_timestamp
    - Evaluation Rubric: Acceptable, Partially Acceptable, Non-Acceptable
    - Feedback Loop: Explains why response was 'Partially Acceptable' before allowing video resumption
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    track: Literal["Care-giving", "Academic", "Food/Tech"] = Field(
        ..., description="Coaching track from video hub"
    )
    topic: str = Field(
        ..., description="Topic for Socratic questioning (e.g., 'omotenashi', 'knowledge_base')"
    )
    video_timestamp: Optional[float] = Field(
        default=None, description="Video timestamp in seconds when 'Practice Now' was clicked"
    )
    candidate_response: Optional[str] = Field(
        default=None, description="Candidate's response to the previous question (if continuing a dialogue)"
    )
    start_new_session: bool = Field(
        default=True, description="If True, starts a new Socratic dialogue session"
    )

    def _get_initial_question(self, topic: str, db: Session) -> Optional[str]:
        """
        Get initial question for high-stakes scenarios from Syllabus.
        
        Checks the Syllabus table for scenarios with initial questions.
        For Food/Tech track, provides default HACCP temperature monitoring question.
        """
        try:
            # Food/Tech Track Default: Temperature log scenario for HACCP training
            if self.track == "Food/Tech" and (not topic or topic == "food_safety" or topic == "haccp"):
                return "The temperature log shows the walk-in freezer at -10°C. Is this acceptable under Japanese standards? If not, what is the corrective action?"
            
            # Check if this topic has an initial question in the Syllabus
            syllabus_entry = db.query(Syllabus).filter(
                Syllabus.topic == topic,
                Syllabus.track == self.track
            ).first()
            
            if syllabus_entry and syllabus_entry.lesson_description:
                # Parse description for initial question
                # Format: "Initial: '...' | Follow-up: '...'"
                description = syllabus_entry.lesson_description
                if "Initial:" in description:
                    parts = description.split("Initial:")
                    if len(parts) > 1:
                        initial_text = parts[1].split("|")[0].strip()  # Get text before "|"
                        # Remove quotes if present
                        if initial_text.startswith("'") and initial_text.endswith("'"):
                            initial_text = initial_text[1:-1]
                        elif initial_text.startswith('"') and initial_text.endswith('"'):
                            initial_text = initial_text[1:-1]
                        return initial_text
            
            return None
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting initial question: {e}")
            return None

    def _get_probing_question(self, topic: str, db: Session) -> Optional[str]:
        """
        Get probing question for high-stakes scenarios.
        
        Checks the Syllabus table for scenarios with probing questions.
        """
        try:
            # Check if this topic has a probing question in the Syllabus
            syllabus_entry = db.query(Syllabus).filter(
                Syllabus.topic == topic,
                Syllabus.track == self.track
            ).first()
            
            if syllabus_entry and syllabus_entry.lesson_description:
                # Parse description for probing question
                # Format: "Initial: '...' | Follow-up: '...'"
                description = syllabus_entry.lesson_description
                if "Follow-up:" in description:
                    parts = description.split("Follow-up:")
                    if len(parts) > 1:
                        probing_text = parts[1].strip()
                        # Remove quotes if present
                        if probing_text.startswith("'") and probing_text.endswith("'"):
                            probing_text = probing_text[1:-1]
                        elif probing_text.startswith('"') and probing_text.endswith('"'):
                            probing_text = probing_text[1:-1]
                        return probing_text
            
            # Also check for explicit probing_question field in scenario data
            # (if stored in JSON or separate field)
            return None
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting probing question: {e}")
            return None

    def _evaluate_response_with_rubric(
        self, 
        candidate_response: str, 
        question_context: str,
        track: str
    ) -> dict:
        """
        Evaluate candidate response using the three-tier rubric.
        
        Returns:
            {
                "status": "Acceptable" | "Partially Acceptable" | "Non-Acceptable",
                "explanation": "Detailed explanation of the evaluation",
                "feedback": "Specific feedback for improvement",
                "can_resume_video": bool
            }
        """
        if not GEMINI_AVAILABLE or not config.GEMINI_API_KEY:
            # Fallback evaluation without Gemini
            return {
                "status": "Partially Acceptable",
                "explanation": "Evaluation service unavailable. Please review your response for correct vocabulary, tone, and grammar.",
                "feedback": "Ensure you use appropriate vocabulary and tone for the track context.",
                "affected_skills": ["Vocabulary", "Tone/Honorifics", "Contextual Logic"],
                "can_resume_video": False
            }
        
        try:
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            
            # Build evaluation prompt based on track
            track_context = {
                "Care-giving": {
                    "tone_requirement": "Use polite, respectful language (Desu/Masu form). Tone should be gentle and caring.",
                    "vocabulary_focus": "Caregiving terminology, patient communication, respect for dignity"
                },
                "Academic": {
                    "tone_requirement": "Use formal academic language (Desu/Masu form). Tone should be professional and clear.",
                    "vocabulary_focus": "Academic terminology, formal expressions, structured communication"
                },
                "Food/Tech": {
                    "tone_requirement": "Use professional workplace language. Can use Plain form in technical contexts, but Desu/Masu for customer-facing situations.",
                    "vocabulary_focus": "Japanese Food Safety (HACCP) terminology, Kitchen Operations vocabulary, temperature monitoring, food handling protocols, sanitation procedures, Commercial Center standards"
                }
            }
            
            track_info = track_context.get(track, track_context["Care-giving"])
            
            evaluation_prompt = f"""You are evaluating a Japanese language response in the context of {track} training.

**Question Context:**
{question_context}

**Candidate Response:**
{candidate_response}

**Evaluation Rubric:**

1. **Acceptable**: 
   - Correct vocabulary appropriate for the {track} context
   - Appropriate tone ({track_info['tone_requirement']})
   - Grammar is correct
   - Meaning is clear and accurate

2. **Partially Acceptable**:
   - Grammar is correct
   - BUT tone is wrong (e.g., used Plain form when Desu/Masu was required, or vice versa)
   - OR vocabulary is slightly off but meaning is preserved
   - Meaning is still understandable

3. **Non-Acceptable**:
   - Meaning is lost or incorrect
   - Wrong terminology used
   - Grammar errors that affect comprehension
   - Response doesn't address the question

**Track-Specific Requirements:**
- Tone: {track_info['tone_requirement']}
- Vocabulary Focus: {track_info['vocabulary_focus']}

Evaluate the candidate's response and provide:
1. Status: One of "Acceptable", "Partially Acceptable", or "Non-Acceptable"
2. Explanation: Why this status was assigned
3. Feedback: Specific guidance on what needs improvement (if not Acceptable)
4. Affected Skills: List which skill categories were affected (can be multiple): "Vocabulary", "Tone/Honorifics", "Contextual Logic"

Respond in JSON format:
{{
    "status": "Acceptable|Partially Acceptable|Non-Acceptable",
    "explanation": "Detailed explanation",
    "feedback": "Specific feedback for improvement",
    "affected_skills": ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
}}
"""
            
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=evaluation_prompt
            )
            response_text = response.text.strip()
            
            # Parse JSON response
            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                evaluation_result = json.loads(response_text)
                
                status = evaluation_result.get("status", "Partially Acceptable")
                explanation = evaluation_result.get("explanation", "Evaluation completed.")
                feedback = evaluation_result.get("feedback", "Please review your response.")
                affected_skills = evaluation_result.get("affected_skills", [])
                
                # Validate affected_skills
                valid_skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
                affected_skills = [s for s in affected_skills if s in valid_skills]
                
                # If no skills specified but status is not Acceptable, infer from feedback
                if not affected_skills and status != "Acceptable":
                    # Infer from feedback keywords
                    feedback_lower = feedback.lower()
                    explanation_lower = explanation.lower()
                    
                    if any(kw in feedback_lower or kw in explanation_lower for kw in ["vocabulary", "terminology", "word", "term"]):
                        affected_skills.append("Vocabulary")
                    if any(kw in feedback_lower or kw in explanation_lower for kw in ["tone", "honorific", "desu", "masu", "plain", "keigo", "polite", "formal"]):
                        affected_skills.append("Tone/Honorifics")
                    if any(kw in feedback_lower or kw in explanation_lower for kw in ["meaning", "context", "logic", "understand", "comprehension"]):
                        affected_skills.append("Contextual Logic")
                    
                    # If still no skills, default to all
                    if not affected_skills:
                        affected_skills = valid_skills.copy()
                
                # Determine if video can be resumed
                can_resume_video = status == "Acceptable"
                
                return {
                    "status": status,
                    "explanation": explanation,
                    "feedback": feedback,
                    "affected_skills": affected_skills,
                    "can_resume_video": can_resume_video
                }
                
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "status": "Partially Acceptable",
                    "explanation": response_text[:500],  # Use first 500 chars
                    "feedback": "Please review the explanation above and try again.",
                    "affected_skills": ["Vocabulary", "Tone/Honorifics", "Contextual Logic"],
                    "can_resume_video": False
                }
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in Gemini evaluation: {e}")
            
            return {
                "status": "Partially Acceptable",
                "explanation": f"Evaluation service error: {str(e)}. Please review your response manually.",
                "feedback": "Ensure correct vocabulary, tone, and grammar for the track context.",
                "affected_skills": ["Vocabulary", "Tone/Honorifics", "Contextual Logic"],
                "can_resume_video": False
            }

    def run(self) -> str:
        """
        Conduct video-triggered Socratic Assessment with evaluation rubric.
        
        Returns assessment result with evaluation status and feedback.
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

            # Create session snapshot
            session_snapshot = {
                "track": self.track,
                "topic": self.topic,
                "video_timestamp": self.video_timestamp,
                "session_start": datetime.now(timezone.utc).isoformat(),
                "source": "video_hub"
            }

            # If candidate provided a response, evaluate it
            if self.candidate_response:
                # Get the last question for context
                question_context = "Previous question context"
                last_entry = None
                if dialogue_history and len(dialogue_history) > 0:
                    last_entry = dialogue_history[-1]
                    question_context = last_entry.get("question", {}).get("text", "Previous question")
                    
                    # Evaluate response using rubric
                    evaluation = self._evaluate_response_with_rubric(
                        candidate_response=self.candidate_response,
                        question_context=question_context,
                        track=self.track
                    )
                    
                    # Update last entry with response and evaluation
                    last_entry["candidate_answer"] = self.candidate_response
                    last_entry["answer_timestamp"] = datetime.now(timezone.utc).isoformat()
                    last_entry["evaluation"] = evaluation
                    last_entry["session_snapshot"] = session_snapshot
                    
                    # Check if this is a high-stakes scenario with probing logic
                    probing_question = None
                    if last_entry.get("is_initial_question", False):
                        # Check if there's a probing question for this topic
                        probing_question = self._get_probing_question(self.topic, db)
                    
                    # Save to database
                    curriculum.dialogue_history = dialogue_history
                    db.commit()
                    
                    # Build response message
                    result = f"### 📝 Response Evaluation\n\n"
                    result += f"**Status:** {evaluation['status']}\n\n"
                    result += f"**Explanation:**\n{evaluation['explanation']}\n\n"
                    
                    if evaluation['status'] != "Acceptable":
                        result += f"**Feedback:**\n{evaluation['feedback']}\n\n"
                    
                    # Probing Logic: If response is Acceptable or Partially Acceptable, ask follow-up
                    if probing_question and (evaluation['status'] == "Acceptable" or evaluation['status'] == "Partially Acceptable"):
                        result += "---\n\n"
                        result += "🔍 **Follow-up Question (Probing Logic):**\n\n"
                        result += f"{probing_question}\n\n"
                        result += "Please provide your response to this follow-up question.\n\n"
                        
                        # Add probing question to dialogue history
                        probing_entry = {
                            "question_id": f"video_probing_{len(dialogue_history) + 1}",
                            "question": {
                                "text": probing_question,
                                "type": "probing",
                                "context": "Follow-up question based on initial response"
                            },
                            "question_timestamp": datetime.now(timezone.utc).isoformat(),
                            "session_snapshot": session_snapshot,
                            "track": self.track,
                            "is_probing_question": True
                        }
                        dialogue_history.append(probing_entry)
                        curriculum.dialogue_history = dialogue_history
                        db.commit()
                        
                        return result
                    
                    # Feedback loop: If Partially Acceptable, require acknowledgment
                    if evaluation['status'] == "Partially Acceptable":
                        result += "---\n\n"
                        result += "⚠️ **Feedback Required:**\n\n"
                        result += "Your response was **Partially Acceptable**. "
                        result += "Please review the feedback above before continuing. "
                        result += "You must acknowledge this feedback before resuming the video.\n\n"
                        result += "**Why this matters:**\n"
                        result += f"- {evaluation['feedback']}\n\n"
                        result += "Once you understand the feedback, you can continue with the assessment."
                    
                    elif evaluation['status'] == "Non-Acceptable":
                        result += "---\n\n"
                        result += "❌ **Response Needs Improvement:**\n\n"
                        result += "Your response was **Non-Acceptable**. "
                        result += "Please review the feedback and try again with the correct vocabulary, tone, and grammar.\n\n"
                        result += "**Key Issues:**\n"
                        result += f"- {evaluation['feedback']}\n\n"
                        result += "You can try answering the question again."
                    
                    else:  # Acceptable
                        result += "---\n\n"
                        result += "✅ **Excellent!** Your response was **Acceptable**. "
                        result += "You can continue with the next question or resume the video.\n\n"
                    
                    return result
                else:
                    # No previous question, create new entry
                    dialogue_history.append({
                        "candidate_answer": self.candidate_response,
                        "answer_timestamp": datetime.now(timezone.utc).isoformat(),
                        "session_snapshot": session_snapshot
                    })
                    curriculum.dialogue_history = dialogue_history
                    db.commit()
                    return "Response recorded. Please start a new question session."

            # Start new question session
            # Import SocraticQuestioningTool to get questions
            try:
                from agency.training_agent.socratic_questioning_tool import SocraticQuestioningTool
                
                # Get question using SocraticQuestioningTool's logic
                socratic_tool = SocraticQuestioningTool(
                    candidate_id=self.candidate_id,
                    topic=self.topic,
                    start_new_session=False  # Don't reset, we're managing the session
                )
                
                # Check if this is a high-stakes scenario with initial question in Syllabus
                initial_question = self._get_initial_question(self.topic, db)
                
                if initial_question:
                    # Use initial question from Syllabus
                    question_text = initial_question
                    question_data = {
                        "text": question_text,
                        "type": "initial",
                        "context": f"High-stakes interview scenario: {self.topic.replace('_', ' ').title()}"
                    }
                else:
                    # Get question using SocraticQuestioningTool's logic
                    question_data = socratic_tool._get_question_by_topic(self.topic, len(dialogue_history), db)
                
                if not question_data:
                    return "No questions available for this topic. Please try a different topic."
                
                # Create question entry with session snapshot
                question_entry = {
                    "question_id": f"video_{len(dialogue_history) + 1}",
                    "question": question_data,
                    "question_timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_snapshot": session_snapshot,
                    "track": self.track,
                    "is_initial_question": initial_question is not None  # Mark as initial for probing logic
                }
                
                dialogue_history.append(question_entry)
                curriculum.dialogue_history = dialogue_history
                db.commit()
                
                # Format question for display
                result = f"### 🎯 Socratic Assessment - {self.track} Track\n\n"
                result += f"**Topic:** {self.topic.replace('_', ' ').title()}\n"
                if self.video_timestamp:
                    minutes = int(self.video_timestamp // 60)
                    seconds = int(self.video_timestamp % 60)
                    result += f"**Video Timestamp:** {minutes}:{seconds:02d}\n\n"
                result += "---\n\n"
                result += f"**Question:**\n\n"
                result += f"{question_data.get('text', question_data.get('question', 'No question available'))}\n\n"
                
                if question_data.get('context'):
                    result += f"**Context:**\n{question_data.get('context')}\n\n"
                
                result += "---\n\n"
                result += "💡 **Instructions:**\n"
                result += "Please provide your response. The system will evaluate:\n"
                result += "- ✅ **Acceptable**: Correct vocabulary and tone\n"
                result += "- ⚠️ **Partially Acceptable**: Correct grammar but wrong tone\n"
                result += "- ❌ **Non-Acceptable**: Meaning lost or incorrect terminology\n\n"
                
                if initial_question:
                    result += "🔍 **Note:** This is a high-stakes interview scenario. After your initial response, you may receive a follow-up probing question.\n\n"
                
                return result
                
            except ImportError:
                return "Error: SocraticQuestioningTool not available. Cannot generate questions."
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in VideoSocraticAssessmentTool: {e}")
            return f"Error conducting assessment: {str(e)}"
        finally:
            db.close()

