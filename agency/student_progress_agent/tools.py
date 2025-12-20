"""
Tools for StudentProgressAgent: Record progress and analytics.

Implements:
- RecordProgress: Save scores and feedback to student_performance table
- StudentAnalytics: Calculate average scores and identify weak words
"""

from __future__ import annotations

import os
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.db_manager import Candidate, KnowledgeBase, SessionLocal, StudentPerformance


class RecordProgress(BaseTool):
    """
    Record student performance for a word/concept.
    
    Saves score, feedback, and transcript to student_performance table
    for RAG-based curriculum prioritization.
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    word_title: str = Field(..., description="Word/concept title (e.g., '病院')")
    score: int = Field(..., description="Grade from 1-10", ge=1, le=10)
    feedback: Optional[str] = Field(default=None, description="General feedback")
    accuracy_feedback: Optional[str] = Field(default=None, description="Accuracy-specific feedback")
    grammar_feedback: Optional[str] = Field(default=None, description="Grammar-specific feedback")
    pronunciation_hint: Optional[str] = Field(default=None, description="Pronunciation hint")
    transcript: Optional[str] = Field(default=None, description="Candidate's transcribed answer")
    language_code: str = Field(default="ja-JP", description="Language code")
    category: Optional[str] = Field(default=None, description="Category (e.g., 'jlpt_n5_vocabulary')")

    def run(self) -> str:
        """Record performance in student_performance table."""
        db: Session = SessionLocal()
        try:
            # Verify candidate exists
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Error: Candidate {self.candidate_id} not found."

            # Try to find word in knowledge_base
            word = db.query(KnowledgeBase).filter(
                KnowledgeBase.concept_title == self.word_title
            ).first()

            word_id = word.id if word else None

            # Create performance record
            performance = StudentPerformance(
                candidate_id=self.candidate_id,
                word_id=word_id,
                word_title=self.word_title,
                score=self.score,
                feedback=self.feedback,
                accuracy_feedback=self.accuracy_feedback,
                grammar_feedback=self.grammar_feedback,
                pronunciation_hint=self.pronunciation_hint,
                transcript=self.transcript,
                language_code=self.language_code,
                category=self.category or (word.category if word else None),
            )

            db.add(performance)
            db.commit()

            return f"✅ Performance recorded: {self.word_title} - Score: {self.score}/10"

        except Exception as e:
            db.rollback()
            return f"Error recording progress: {str(e)}"
        finally:
            db.close()


class StudentAnalytics(BaseTool):
    """
    Calculate analytics for a student's performance.
    
    Features:
    - Average score per JLPT level/category
    - Identify weak words (score < 6 or not attempted)
    - Performance trends over time
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    category: Optional[str] = Field(
        default=None,
        description="Filter by category (e.g., 'jlpt_n5_vocabulary'). If None, analyzes all categories."
    )

    def run(self) -> str:
        """Calculate and return student analytics."""
        db: Session = SessionLocal()
        try:
            # Verify candidate exists
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Error: Candidate {self.candidate_id} not found."

            # Build query
            query = db.query(StudentPerformance).filter(
                StudentPerformance.candidate_id == self.candidate_id
            )

            if self.category:
                query = query.filter(StudentPerformance.category == self.category)

            all_performances = query.all()

            if not all_performances:
                return f"📊 No performance records found for candidate {self.candidate_id}."

            # Calculate average score per category
            category_avg = {}
            category_counts = {}

            for perf in all_performances:
                cat = perf.category or "uncategorized"
                if cat not in category_avg:
                    category_avg[cat] = 0
                    category_counts[cat] = 0
                category_avg[cat] += perf.score
                category_counts[cat] += 1

            # Calculate averages
            for cat in category_avg:
                category_avg[cat] = round(category_avg[cat] / category_counts[cat], 2)

            # Identify weak words (score < 6)
            weak_words = [
                perf for perf in all_performances
                if perf.score < 6
            ]

            # Get words not attempted yet (from knowledge_base but not in performance)
            attempted_word_titles = {perf.word_title for perf in all_performances if perf.word_title}
            
            kb_query = db.query(KnowledgeBase)
            if self.category:
                kb_query = kb_query.filter(KnowledgeBase.category == self.category)
            
            all_words = kb_query.all()
            not_attempted = [
                word for word in all_words
                if word.concept_title not in attempted_word_titles
            ]

            # Format results
            result = f"📊 Student Analytics for {candidate.full_name} ({self.candidate_id})\n"
            result += "=" * 60 + "\n\n"

            result += "**Average Scores by Category:**\n"
            for cat, avg_score in sorted(category_avg.items()):
                result += f"  • {cat}: {avg_score}/10 ({category_counts[cat]} attempts)\n"
            result += "\n"

            result += f"**Weak Words (Score < 6):** {len(weak_words)}\n"
            if weak_words:
                for perf in weak_words[:10]:  # Show top 10
                    result += f"  • {perf.word_title}: {perf.score}/10\n"
                if len(weak_words) > 10:
                    result += f"  ... and {len(weak_words) - 10} more\n"
            result += "\n"

            result += f"**Words Not Attempted:** {len(not_attempted)}\n"
            if not_attempted:
                for word in not_attempted[:10]:  # Show top 10
                    result += f"  • {word.concept_title}\n"
                if len(not_attempted) > 10:
                    result += f"  ... and {len(not_attempted) - 10} more\n"

            return result

        except Exception as e:
            return f"Error calculating analytics: {str(e)}"
        finally:
            db.close()


class GetCurrentPhase(BaseTool):
    """
    Determine the current curriculum phase for a student based on performance.
    
    Phase System:
    - Phase 1 (N5 Basics): Current if Average Score < 6.0
    - Phase 2 (Caregiving Essentials): Unlocked when N5 Average ≥ 6.0 AND at least 20 words attempted
    - Phase 3 (Scenario Mastery): Unlocked when Caregiving Average ≥ 7.5
    
    Returns phase number, unlock status, and progress to next phase.
    """

    candidate_id: str = Field(..., description="Candidate identifier")

    def run(self) -> str:
        """Determine current phase and return phase info with progress."""
        db: Session = SessionLocal()
        try:
            # Verify candidate exists
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Error: Candidate {self.candidate_id} not found."

            # Get all performance records
            performances = db.query(StudentPerformance).filter(
                StudentPerformance.candidate_id == self.candidate_id
            ).all()

            # Calculate Phase 1 (N5 Basics) metrics
            n5_performances = [
                p for p in performances
                if p.category == "jlpt_n5_vocabulary"
            ]
            
            n5_avg = 0.0
            n5_count = len(n5_performances)
            if n5_performances:
                n5_avg = sum(p.score for p in n5_performances) / len(n5_performances)

            # Calculate Phase 2 (Caregiving Essentials) metrics
            caregiving_performances = [
                p for p in performances
                if p.category == "caregiving_vocabulary"
            ]
            
            caregiving_avg = 0.0
            caregiving_count = len(caregiving_performances)
            if caregiving_performances:
                caregiving_avg = sum(p.score for p in caregiving_performances) / len(caregiving_performances)

            # Determine current phase
            current_phase = 1
            phase_unlocked = [True]  # Phase 1 always unlocked
            
            # Check Phase 2 unlock: N5 Average ≥ 6.0 AND at least 20 words attempted
            phase_2_unlocked = n5_avg >= 6.0 and n5_count >= 20
            phase_unlocked.append(phase_2_unlocked)
            
            if phase_2_unlocked:
                current_phase = 2
                
                # Check Phase 3 unlock: Caregiving Average ≥ 7.5
                phase_3_unlocked = caregiving_avg >= 7.5
                phase_unlocked.append(phase_3_unlocked)
                
                if phase_3_unlocked:
                    current_phase = 3

            # Calculate progress to next phase
            next_phase_progress = {}
            
            if current_phase == 1:
                # Progress to Phase 2: Need N5 avg ≥ 6.0 AND 20 words
                avg_progress = min(100, (n5_avg / 6.0) * 100) if n5_avg < 6.0 else 100
                count_progress = min(100, (n5_count / 20) * 100)
                next_phase_progress = {
                    "phase": 2,
                    "avg_progress": avg_progress,
                    "count_progress": count_progress,
                    "overall_progress": min(avg_progress, count_progress),
                    "requirements": {
                        "n5_avg": f"{n5_avg:.1f}/6.0",
                        "n5_count": f"{n5_count}/20",
                    }
                }
            elif current_phase == 2:
                # Progress to Phase 3: Need Caregiving avg ≥ 7.5
                avg_progress = min(100, (caregiving_avg / 7.5) * 100) if caregiving_avg < 7.5 else 100
                next_phase_progress = {
                    "phase": 3,
                    "avg_progress": avg_progress,
                    "overall_progress": avg_progress,
                    "requirements": {
                        "caregiving_avg": f"{caregiving_avg:.1f}/7.5",
                    }
                }
            else:
                # Phase 3 - max phase reached
                next_phase_progress = {
                    "phase": None,
                    "overall_progress": 100,
                    "message": "Maximum phase reached"
                }

            # Format result as JSON-like string for easy parsing
            import json
            result_dict = {
                "current_phase": current_phase,
                "phase_unlocked": phase_unlocked,
                "next_phase_progress": next_phase_progress,
                "metrics": {
                    "n5_avg": round(n5_avg, 2),
                    "n5_count": n5_count,
                    "caregiving_avg": round(caregiving_avg, 2),
                    "caregiving_count": caregiving_count,
                }
            }
            
            return json.dumps(result_dict, indent=2)

        except Exception as e:
            return f"Error determining phase: {str(e)}"
        finally:
            db.close()


class GenerateDailyBriefing(BaseTool):
    """
    Generate a daily executive summary briefing for a student's progress.
    
    Queries student_performance table for last 24 hours, analyzes performance,
    and uses Gemini 2.5 Flash to generate a 3-sentence summary.
    """

    candidate_id: str = Field(..., description="Candidate identifier")

    def run(self) -> str:
        """Generate daily briefing summary."""
        db: Session = SessionLocal()
        try:
            # Verify candidate exists
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Error: Candidate {self.candidate_id} not found."

            # Query performance records from last 24 hours
            from datetime import datetime, timedelta, timezone
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            recent_performances = db.query(StudentPerformance).filter(
                StudentPerformance.candidate_id == self.candidate_id,
                StudentPerformance.created_at >= cutoff_time
            ).order_by(StudentPerformance.created_at.desc()).all()

            if not recent_performances:
                return f"📊 No activity in the last 24 hours for {candidate.full_name}. Start practicing to generate a briefing!"

            # Collect data for briefing
            word_count = len(recent_performances)
            scores = [p.score for p in recent_performances]
            average_score = sum(scores) / len(scores) if scores else 0
            
            weak_words = [p.word_title for p in recent_performances if p.score < 6]
            weak_words_list = list(set(weak_words))  # Remove duplicates
            
            # Collect feedback points
            feedback_points = []
            for p in recent_performances:
                if p.accuracy_feedback:
                    feedback_points.append(f"Accuracy: {p.accuracy_feedback[:100]}...")
                if p.grammar_feedback:
                    feedback_points.append(f"Grammar: {p.grammar_feedback[:100]}...")
            
            # Get current phase and progress
            phase_tool = GetCurrentPhase(candidate_id=self.candidate_id)
            phase_result = phase_tool.run()
            
            import json
            phase_info = json.loads(phase_result)
            current_phase = phase_info.get("current_phase", 1)
            next_phase_progress = phase_info.get("next_phase_progress", {})
            overall_progress = next_phase_progress.get("overall_progress", 0) if next_phase_progress else 0
            
            # Prepare data for Gemini
            performance_summary = {
                "word_count": word_count,
                "average_score": round(average_score, 2),
                "weak_words": weak_words_list[:5],  # Top 5 weak words
                "weak_word_count": len(weak_words_list),
                "current_phase": current_phase,
                "next_phase_progress": round(overall_progress, 1),
                "sample_feedback": feedback_points[:3] if feedback_points else []  # Sample feedback
            }
            
            # Generate briefing using Gemini
            try:
                from google import genai
                import config
                
                api_key = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
                if not api_key:
                    return "Error: GEMINI_API_KEY not found. Please set it in your .env file."
                
                client = genai.Client(api_key=api_key)
                
                prompt = f"""You are an executive coach writing a daily progress briefing for a Japanese language learning student.

**Student Name:** {candidate.full_name}
**Candidate ID:** {self.candidate_id}

**Today's Performance (Last 24 Hours):**
- Words Practiced: {performance_summary['word_count']}
- Average Score: {performance_summary['average_score']}/10
- Weak Words (Score < 6): {performance_summary['weak_word_count']} words
- Current Phase: Phase {performance_summary['current_phase']}
- Progress to Next Phase: {performance_summary['next_phase_progress']}%

**Weak Words Needing Attention:**
{', '.join(performance_summary['weak_words']) if performance_summary['weak_words'] else 'None'}

**Sample AI Feedback:**
{chr(10).join(performance_summary['sample_feedback'][:2]) if performance_summary['sample_feedback'] else 'No specific feedback available'}

**Instructions:**
Write a concise 3-sentence executive summary in the following format:
1. First sentence: State how many words were practiced today and overall performance.
2. Second sentence: Mention progress toward next phase (if applicable) or current phase status.
3. Third sentence: Highlight specific areas needing improvement (weak words, feedback points).

**Tone:** Professional, encouraging, and actionable. Use the student's name naturally.

**Output:** Only the 3-sentence summary, no additional text or formatting.
"""
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                
                briefing_text = response.text.strip()
                
                # Clean up any markdown formatting if present
                if "```" in briefing_text:
                    lines = briefing_text.split("\n")
                    briefing_text = "\n".join([line for line in lines if not line.strip().startswith("```")])
                
                # Log briefing generation for admin monitoring
                try:
                    from utils.activity_logger import ActivityLogger
                    ActivityLogger.log_briefing(
                        candidate_id=self.candidate_id,
                        word_count=word_count,
                        average_score=average_score,
                    )
                except Exception:
                    pass  # Don't fail if logging fails
                
                return briefing_text
                
            except ImportError:
                return "Error: google-genai package not installed. Please install it to generate briefings."
            except Exception as e:
                return f"Error generating briefing: {str(e)}"

        except Exception as e:
            return f"Error generating daily briefing: {str(e)}"
        finally:
            db.close()

