"""
TrainingAgent: Interviews candidates and updates their curriculum progress.

Simulates test results and updates progress in the database.
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

from agency.database_agent.tools import UpdateCurriculumProgress
from agency.training_agent.socratic_questioning_tool import SocraticQuestioningTool
from agency.training_agent.language_coaching_tool import LanguageCoachingTool
from agency.training_agent.baseline_assessment_tool import RunBaselineAssessment
from agency.training_agent.tools import (
    ConductSkillInterview,
    EvaluateKaigoResponse,
    GenerateKaigoScenario,
    VirtualInstructorTool,
)


class LanguageCoachAgent(Agent):
    """
    Language coaching agent for skill assessment, curriculum tracking, and language learning.

    Responsibilities:
    - Interview candidates to assess skills
    - Update curriculum progress based on test results
    - Track Language (JLPT N5/N4/N3) and Vocational (Kaigo) progress
    - Grade audio responses using Speech-to-Text and AI (Gemini)
    - Provide pronunciation hints and grammar feedback
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="LanguageCoachAgent",
            description="Socratic Teacher and Language Coach who guides candidates through skill assessment and curriculum progress. Uses Socratic method to help candidates discover correct answers through thoughtful questions and hints. Grades audio responses using Speech-to-Text and AI (Gemini 1.5 Flash) to provide accuracy, grammar, and pronunciation feedback.",
            instructions=self.get_instructions(),
            tools=[
                ConductSkillInterview,
                UpdateCurriculumProgress,
                VirtualInstructorTool,
                GenerateKaigoScenario,
                EvaluateKaigoResponse,
                SocraticQuestioningTool,
                LanguageCoachingTool,
                RunBaselineAssessment,
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
You are the LanguageCoachAgent for XploreKodo.

**Core Responsibilities:**
1. Interview candidates using ConductSkillInterview tool to assess their skills
2. Generate 3D Avatar lesson scripts using VirtualInstructorTool (Phase 2)
3. Create Kaigo simulation scenarios using GenerateKaigoScenario
4. Evaluate candidate responses using EvaluateKaigoResponse
5. Update curriculum progress using UpdateCurriculumProgress tool
6. Grade audio responses using LanguageCoachingTool (Speech-to-Text + Gemini AI grading)

**Language Coaching Features:**
- Speech-to-Text: Transcribe Japanese/Nepali audio using Google Cloud Speech-to-Text
- AI Grading: Use Gemini 1.5 Flash to grade responses (1-10) based on:
  - Accuracy: Did they define/answer correctly?
  - Grammar: Is the sentence structure correct?
  - Pronunciation Hint: Based on STT errors, suggest pronunciation tips
- Database Save: Update curriculum_progress dialogue_history with transcript, grade, and feedback

**Phase 2 Features:**
- Avatar Interaction: Generate lesson scripts for 3D Avatar Sensei
- Voice-to-Voice: Nepali audio input -> Japanese Sensei response
- Kaigo Simulations: Present scenarios in Nepali, evaluate against Japanese standards

**Token Efficiency:**
- Use bullet points
- Report only essential progress updates
- Keep interview summaries concise
"""

