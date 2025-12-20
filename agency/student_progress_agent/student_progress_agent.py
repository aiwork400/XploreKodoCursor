"""
StudentProgressAgent: Memory Layer and Analytics for RAG-based Curriculum.

Responsibilities:
- Record student performance for words/concepts
- Calculate analytics (average scores, weak words, not attempted)
- Support RAG-based curriculum prioritization
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

from agency.student_progress_agent.tools import RecordProgress, StudentAnalytics, GetCurrentPhase, GenerateDailyBriefing


class StudentProgressAgent(Agent):
    """
    Student progress tracking agent for Memory Layer and RAG-based curriculum.
    
    Features:
    - Records individual word/concept performance
    - Calculates analytics per JLPT level/category
    - Identifies weak words and not-attempted words for curriculum prioritization
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="StudentProgressAgent",
            description="Memory Layer agent that tracks student performance, calculates analytics, and identifies weak words for RAG-based curriculum prioritization.",
            instructions=self.get_instructions(),
            tools=[
                RecordProgress,
                StudentAnalytics,
                GetCurrentPhase,
                GenerateDailyBriefing,
            ],
            **kwargs,
        )

    def get_instructions(self) -> str:
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()

        return """
You are the StudentProgressAgent for XploreKodo.

**Core Responsibilities:**
1. Record student performance using RecordProgress tool after each grading session
2. Calculate analytics using StudentAnalytics tool to identify:
   - Average scores per JLPT level/category
   - Weak words (score < 6)
   - Words not yet attempted
3. Support RAG-based curriculum by providing data for word prioritization

**Memory Layer:**
- Every word/concept attempt is recorded in student_performance table
- Scores (1-10), feedback, and transcripts are stored
- This data enables personalized curriculum that prioritizes weak/untried words

**Analytics:**
- Calculate average scores per category (e.g., jlpt_n5_vocabulary)
- Identify words with score < 6 as "weak words"
- List words from knowledge_base that haven't been attempted yet
- Provide insights for curriculum adaptation

**Integration:**
- LanguageCoachAgent calls RecordProgress after each grading session
- SocraticQuestioningTool uses analytics to prioritize questions
- Dashboard visualizes learning curves and weak areas
"""

