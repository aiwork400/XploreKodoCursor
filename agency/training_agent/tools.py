"""
Tools for TrainingAgent: Skill interview, avatar interaction, and Kaigo simulation.
"""

from __future__ import annotations

from typing import Literal, Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, SessionLocal
from mvp_v1.training.advisory_knowledge_base import AdvisoryKnowledgeBase


class ConductSkillInterview(BaseTool):
    """
    Conducts a skill interview with a candidate and simulates test results.

    Updates curriculum progress based on interview performance.
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    interview_type: Literal["language", "vocational"] = Field(..., description="Type of interview: 'language' or 'vocational'")
    language_level: Literal["N5", "N4", "N3"] = Field(default="N5", description="JLPT level for language interview")
    vocational_module: Literal["kaigo_basics", "communication_skills", "physical_care"] = Field(
        default="kaigo_basics", description="Vocational module for interview"
    )

    def run(self) -> str:
        """
        Conduct interview and simulate test results.

        In production, this would integrate with actual assessment systems.
        For MVP, simulates results based on candidate profile.
        """
        db: Session = SessionLocal()
        try:
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Candidate {self.candidate_id} not found."

            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == self.candidate_id
            ).first()

            if not curriculum:
                curriculum = CurriculumProgress(candidate_id=self.candidate_id)
                db.add(curriculum)

            result = f"Skill Interview Results for {candidate.full_name} ({self.candidate_id}):\n\n"

            if self.interview_type == "language":
                # Simulate JLPT test results
                simulated_score = 75
                units_to_complete = int((simulated_score / 100) * {
                    "N5": curriculum.jlpt_n5_total_units,
                    "N4": curriculum.jlpt_n4_total_units,
                    "N3": curriculum.jlpt_n3_total_units,
                }[self.language_level])

                if self.language_level == "N5":
                    curriculum.jlpt_n5_units_completed = units_to_complete
                    result += f"JLPT {self.language_level} Interview:\n"
                    result += f"- Score: {simulated_score}%\n"
                    result += f"- Units Completed: {units_to_complete}/{curriculum.jlpt_n5_total_units}\n"
                elif self.language_level == "N4":
                    curriculum.jlpt_n4_units_completed = units_to_complete
                    result += f"JLPT {self.language_level} Interview:\n"
                    result += f"- Score: {simulated_score}%\n"
                    result += f"- Units Completed: {units_to_complete}/{curriculum.jlpt_n4_total_units}\n"
                elif self.language_level == "N3":
                    curriculum.jlpt_n3_units_completed = units_to_complete
                    result += f"JLPT {self.language_level} Interview:\n"
                    result += f"- Score: {simulated_score}%\n"
                    result += f"- Units Completed: {units_to_complete}/{curriculum.jlpt_n3_total_units}\n"

            elif self.interview_type == "vocational":
                simulated_score = 80
                lessons_to_complete = int((simulated_score / 100) * {
                    "kaigo_basics": curriculum.kaigo_basics_total_lessons,
                    "communication_skills": curriculum.communication_skills_total_lessons,
                    "physical_care": curriculum.physical_care_total_lessons,
                }[self.vocational_module])

                module_name = self.vocational_module.replace("_", " ").title()
                if self.vocational_module == "kaigo_basics":
                    curriculum.kaigo_basics_lessons_completed = lessons_to_complete
                    result += f"{module_name} Interview:\n"
                    result += f"- Score: {simulated_score}%\n"
                    result += f"- Lessons Completed: {lessons_to_complete}/{curriculum.kaigo_basics_total_lessons}\n"
                elif self.vocational_module == "communication_skills":
                    curriculum.communication_skills_lessons_completed = lessons_to_complete
                    result += f"{module_name} Interview:\n"
                    result += f"- Score: {simulated_score}%\n"
                    result += f"- Lessons Completed: {lessons_to_complete}/{curriculum.communication_skills_total_lessons}\n"
                elif self.vocational_module == "physical_care":
                    curriculum.physical_care_lessons_completed = lessons_to_complete
                    result += f"{module_name} Interview:\n"
                    result += f"- Score: {simulated_score}%\n"
                    result += f"- Lessons Completed: {lessons_to_complete}/{curriculum.physical_care_total_lessons}\n"

            db.commit()
            result += "\n✓ Progress updated in database."

            return result
        except Exception as e:
            db.rollback()
            return f"Error conducting interview: {str(e)}"
        finally:
            db.close()


class VirtualInstructorTool(BaseTool):
    """
    Generates lesson scripts for 3D Avatar interaction.

    Creates scripts based on the candidate's current JLPT or Kaigo module progress.
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    module_type: Literal["jlpt", "kaigo"] = Field(..., description="Module type: 'jlpt' or 'kaigo'")
    jlpt_level: Optional[Literal["N5", "N4", "N3"]] = Field(default=None, description="JLPT level (if module_type='jlpt')")
    kaigo_module: Optional[Literal["kaigo_basics", "communication_skills", "physical_care"]] = Field(
        default=None, description="Kaigo module (if module_type='kaigo')"
    )

    def run(self) -> str:
        """
        Generate lesson script for 3D Avatar based on candidate's current progress.

        Returns structured script with dialogue, gestures, and interaction points.
        """
        db: Session = SessionLocal()
        try:
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == self.candidate_id
            ).first()

            if not curriculum:
                return f"Curriculum progress not found for candidate {self.candidate_id}."

            script = f"=== 3D Avatar Lesson Script ===\n"
            script += f"Candidate: {self.candidate_id}\n"
            script += f"Module: {self.module_type}\n\n"

            if self.module_type == "jlpt" and self.jlpt_level:
                # Generate JLPT lesson script
                units_completed = {
                    "N5": curriculum.jlpt_n5_units_completed,
                    "N4": curriculum.jlpt_n4_units_completed,
                    "N3": curriculum.jlpt_n3_units_completed,
                }[self.jlpt_level]
                
                total_units = {
                    "N5": curriculum.jlpt_n5_total_units,
                    "N4": curriculum.jlpt_n4_total_units,
                    "N3": curriculum.jlpt_n3_total_units,
                }[self.jlpt_level]

                current_unit = units_completed + 1 if units_completed < total_units else total_units

                script += f"**JLPT {self.jlpt_level} - Unit {current_unit}/{total_units}**\n\n"
                script += "**Avatar Dialogue (Japanese Sensei):**\n"
                script += f"こんにちは！今日はJLPT {self.jlpt_level}のユニット{current_unit}を勉強しましょう。\n"
                script += "(Hello! Today let's study JLPT {self.jlpt_level} Unit {current_unit}.)\n\n"
                script += "**Key Vocabulary:**\n"
                script += "- [Vocabulary words for this unit]\n"
                script += "- [Grammar points]\n\n"
                script += "**Interaction Points:**\n"
                script += "1. Avatar gestures: Pointing to whiteboard\n"
                script += "2. Student response: Repeat after Sensei\n"
                script += "3. Practice exercise: Fill in the blank\n\n"

            elif self.module_type == "kaigo" and self.kaigo_module:
                # Generate Kaigo lesson script
                module_name = self.kaigo_module.replace("_", " ").title()
                lessons_completed = {
                    "kaigo_basics": curriculum.kaigo_basics_lessons_completed,
                    "communication_skills": curriculum.communication_skills_lessons_completed,
                    "physical_care": curriculum.physical_care_lessons_completed,
                }[self.kaigo_module]
                
                total_lessons = {
                    "kaigo_basics": curriculum.kaigo_basics_total_lessons,
                    "communication_skills": curriculum.communication_skills_total_lessons,
                    "physical_care": curriculum.physical_care_total_lessons,
                }[self.kaigo_module]

                current_lesson = lessons_completed + 1 if lessons_completed < total_lessons else total_lessons

                script += f"**{module_name} - Lesson {current_lesson}/{total_lessons}**\n\n"
                script += "**Avatar Dialogue (Japanese Sensei):**\n"
                script += f"今日は{module_name}のレッスン{current_lesson}です。\n"
                script += f"(Today is {module_name} Lesson {current_lesson}.)\n\n"
                script += "**Key Concepts:**\n"
                script += "- [Caregiving technique]\n"
                script += "- [Communication protocol]\n"
                script += "- [Safety procedures]\n\n"
                script += "**Interaction Points:**\n"
                script += "1. Avatar demonstration: Show proper technique\n"
                script += "2. Student practice: Mimic avatar movements\n"
                script += "3. Scenario roleplay: Practice with virtual patient\n\n"

            script += "**Script Format:**\n"
            script += "- Dialogue: [Japanese text with English translation]\n"
            script += "- Gestures: [Avatar animation cues]\n"
            script += "- Timing: [Pause points for student response]\n"

            return script
        except Exception as e:
            return f"Error generating lesson script: {str(e)}"
        finally:
            db.close()


class GenerateKaigoScenario(BaseTool):
    """
    Generates Kaigo simulation scenarios for candidate practice.

    Creates text-based problems that candidates must respond to in Nepali,
    then evaluates responses against Japanese caregiving standards.
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    scenario_type: Literal["medication_refusal", "patient_fall", "communication_barrier", "hygiene_assistance"] = Field(
        default="medication_refusal", description="Type of Kaigo scenario"
    )

    def run(self) -> str:
        """
        Generate Kaigo scenario and present it to candidate.

        Returns scenario description in Nepali audio script format.
        """
        # Scenario templates
        scenarios = {
            "medication_refusal": {
                "nepali": "रोगीले औषधि लिन अस्वीकार गरेका छन्। तपाईंले के गर्नुहुन्छ?",
                "english": "Patient is refusing medication. What do you do?",
                "japanese_standard": "Calmly explain the importance of medication, check for concerns, and report to supervisor if needed.",
            },
            "patient_fall": {
                "nepali": "रोगीले ठोक्किएर खस्नुभयो। तपाईंले पहिले के गर्नुहुन्छ?",
                "english": "Patient has fallen. What do you do first?",
                "japanese_standard": "Assess patient safety, do not move if injury suspected, call for medical assistance immediately.",
            },
            "communication_barrier": {
                "nepali": "रोगीले जापानी बोल्दैनन् र तपाईंले नेपाली मात्र बुझ्नुहुन्छ। के गर्नुहुन्छ?",
                "english": "Patient doesn't speak Japanese and you only understand Nepali. What do you do?",
                "japanese_standard": "Use simple gestures, visual aids, translation app, and involve interpreter if available.",
            },
            "hygiene_assistance": {
                "nepali": "रोगीले व्यक्तिगत स्वच्छतामा सहयोग चाहनुहुन्छ। तपाईंले कसरी सहयोग गर्नुहुन्छ?",
                "english": "Patient needs assistance with personal hygiene. How do you help?",
                "japanese_standard": "Maintain dignity, ensure privacy, use proper technique, and follow infection control protocols.",
            },
        }

        scenario = scenarios.get(self.scenario_type, scenarios["medication_refusal"])

        result = f"=== Kaigo Simulation Scenario ===\n"
        result += f"Candidate: {self.candidate_id}\n"
        result += f"Scenario Type: {self.scenario_type.replace('_', ' ').title()}\n\n"
        result += "**Nepali Audio Script:**\n"
        result += f"{scenario['nepali']}\n\n"
        result += f"**English Translation:**\n"
        result += f"{scenario['english']}\n\n"
        result += "**Japanese Caregiving Standard (for evaluation):**\n"
        result += f"{scenario['japanese_standard']}\n\n"
        result += "**Instructions:**\n"
        result += "1. Candidate responds in Nepali (audio or text)\n"
        result += "2. System evaluates response against Japanese standards\n"
        result += "3. Score stored in simulation_performance column\n"

        return result


class EvaluateKaigoResponse(BaseTool):
    """
    Evaluates candidate's Kaigo scenario response using Socratic teaching method.

    For partial answers (50%+ correct), generates follow-up hints instead of failing.
    Stores simulation scores in PostgreSQL curriculum_progress.simulation_performance.
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    scenario_type: str = Field(..., description="Type of scenario that was presented")
    candidate_response: str = Field(..., description="Candidate's response (in Nepali or English)")
    score: int = Field(..., description="Evaluation score (0-100)")
    generate_follow_up: bool = Field(
        default=True,
        description="If True, generates Socratic follow-up hints for partial answers (50%+ correct)"
    )

    def run(self) -> str:
        """
        Evaluate response using Socratic method and store simulation performance score.
        For 50%+ correct answers, generates follow-up hints instead of failing.
        """
        db: Session = SessionLocal()
        try:
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == self.candidate_id
            ).first()

            if not curriculum:
                return f"Curriculum progress not found for candidate {self.candidate_id}."

            # Update simulation_performance (stored as JSON or text)
            current_performance = curriculum.simulation_performance or ""
            new_entry = f"{self.scenario_type}:{self.score}"
            
            if current_performance:
                curriculum.simulation_performance = f"{current_performance};{new_entry}"
            else:
                curriculum.simulation_performance = new_entry

            db.commit()

            # Evaluate against Japanese standards using AdvisoryKnowledgeBase
            kb = AdvisoryKnowledgeBase()
            
            # Map scenario type to relevant knowledge base topics
            scenario_topic_map = {
                "medication_refusal": "kaigo_medication_standards",
                "patient_fall": "kaigo_fall_protocol",
                "communication_barrier": "kaigo_communication_standards",
                "hygiene_assistance": "kaigo_hygiene_standards",
            }
            
            relevant_topic = scenario_topic_map.get(self.scenario_type, "kaigo_medication_standards")
            standard_entry = kb.get_entry(relevant_topic)

            evaluation = f"=== Kaigo Response Evaluation (Socratic Method) ===\n"
            evaluation += f"Candidate: {self.candidate_id}\n"
            evaluation += f"Scenario: {self.scenario_type.replace('_', ' ').title()}\n"
            evaluation += f"Score: {self.score}/100\n\n"
            evaluation += "**Response Analysis:**\n"
            evaluation += f"Response: {self.candidate_response}\n\n"
            
            if standard_entry:
                evaluation += "**Japanese Caregiving Standard (Reference):**\n"
                evaluation += f"{standard_entry.title}\n"
                evaluation += f"{standard_entry.content[:300]}...\n\n"
            
            # Socratic Teaching: Generate follow-up hints for partial answers
            if self.score >= 50 and self.score < 80 and self.generate_follow_up:
                evaluation += "**Socratic Guidance (Partial Answer Detected):**\n\n"
                evaluation += "✅ **What You Got Right:**\n"
                
                # Identify what they got right based on score and response
                if "communication" in self.candidate_response.lower() or "talk" in self.candidate_response.lower():
                    evaluation += "- You correctly identified the importance of communication\n"
                if "safety" in self.candidate_response.lower() or "safe" in self.candidate_response.lower():
                    evaluation += "- You prioritized patient safety\n"
                if "respect" in self.candidate_response.lower() or "dignity" in self.candidate_response.lower():
                    evaluation += "- You showed respect for patient dignity\n"
                if "report" in self.candidate_response.lower() or "supervisor" in self.candidate_response.lower():
                    evaluation += "- You recognized the need for reporting\n"
                else:
                    evaluation += "- You demonstrated thoughtful consideration of the situation\n"
                
                evaluation += "\n🤔 **Follow-Up Hint (Socratic Question):**\n"
                
                # Generate scenario-specific follow-up hints
                if self.scenario_type == "medication_refusal":
                    evaluation += "That is a good start! However, in Japan, we must also report this to the supervisor immediately.\n"
                    evaluation += "**Socratic Question:** How would you say 'I will report this to the supervisor' in Japanese?\n"
                    evaluation += "(Hint: 報告します - hōkoku shimasu)\n\n"
                    evaluation += "**Additional Consideration:** What other steps would you take while waiting for the supervisor? Think about patient safety and documentation.\n"
                
                elif self.scenario_type == "patient_fall":
                    evaluation += "Good thinking! However, in Japanese caregiving, we must also assess the patient's condition before moving them.\n"
                    evaluation += "**Socratic Question:** How would you say 'Are you okay?' or 'Can you move?' in Japanese?\n"
                    evaluation += "(Hint: 大丈夫ですか？ - daijōbu desu ka?)\n\n"
                    evaluation += "**Additional Consideration:** What information should you document immediately after a fall incident?\n"
                
                elif self.scenario_type == "communication_barrier":
                    evaluation += "Excellent that you're thinking about communication! In Japan, we also use non-verbal cues and patience.\n"
                    evaluation += "**Socratic Question:** How would you say 'I understand' or 'Take your time' in Japanese?\n"
                    evaluation += "(Hint: 分かりました - wakarimashita, ゆっくり - yukkuri)\n\n"
                    evaluation += "**Additional Consideration:** How would you ensure the patient feels heard and respected, even with a language barrier?\n"
                
                elif self.scenario_type == "hygiene_assistance":
                    evaluation += "Good approach! However, in Japanese caregiving, we must also ensure privacy and dignity throughout the process.\n"
                    evaluation += "**Socratic Question:** How would you say 'I will help you' or 'Let's do this together' in Japanese?\n"
                    evaluation += "(Hint: お手伝いします - otetsudai shimasu)\n\n"
                    evaluation += "**Additional Consideration:** What steps would you take to maintain the patient's privacy and comfort?\n"
                
                else:
                    evaluation += "That is a good start! However, in Japan, we must also consider additional protocols.\n"
                    evaluation += "**Socratic Question:** What other aspects of Japanese caregiving standards should we consider in this situation?\n"
                
                evaluation += "\n📚 **Next Steps:**\n"
                evaluation += "- Reflect on the hint above\n"
                evaluation += "- Try to answer the Socratic question\n"
                evaluation += "- Consider the additional considerations\n"
                evaluation += "- We'll continue this dialogue until you reach the complete answer\n"
                
            elif self.score >= 80:
                evaluation += "**Compliance Assessment:**\n"
                evaluation += "✓ Excellent: Response aligns with Japanese caregiving standards\n"
                evaluation += "  - Demonstrates understanding of Japanese caregiving protocols\n"
                evaluation += "  - Shows cultural sensitivity and proper technique\n"
                evaluation += "  - Includes all necessary steps (communication, safety, reporting, documentation)\n"
                
            elif self.score < 50:
                evaluation += "**Socratic Guidance (Needs More Support):**\n\n"
                evaluation += "✅ **Positive Aspect:**\n"
                evaluation += "- I appreciate that you're thinking about this situation carefully\n\n"
                evaluation += "🔍 **Let's Break This Down Step by Step:**\n"
                evaluation += "1. What is the immediate priority in this situation? (Safety? Communication?)\n"
                evaluation += "2. In Japanese caregiving, we always prioritize patient safety and dignity. How does that apply here?\n"
                evaluation += "3. What would be the first thing you would do?\n\n"
                evaluation += "💡 **Gentle Hint:**\n"
                
                if self.scenario_type == "medication_refusal":
                    evaluation += "Think about: (1) Ensuring patient safety, (2) Communicating clearly, (3) Reporting to supervisor, (4) Documenting the incident.\n"
                elif self.scenario_type == "patient_fall":
                    evaluation += "Think about: (1) Assessing patient condition, (2) Ensuring safety, (3) Not moving patient if injured, (4) Reporting immediately.\n"
                elif self.scenario_type == "communication_barrier":
                    evaluation += "Think about: (1) Using simple language, (2) Non-verbal communication, (3) Patience and empathy, (4) Seeking translation help if needed.\n"
                elif self.scenario_type == "hygiene_assistance":
                    evaluation += "Think about: (1) Privacy and dignity, (2) Patient comfort, (3) Proper technique, (4) Documentation.\n"
                
                evaluation += "\n📚 **Learning Opportunity:**\n"
                evaluation += "- Review the Japanese caregiving standards for this scenario\n"
                evaluation += "- We'll work through this together step by step\n"

            evaluation += f"\n✓ Simulation score stored in database (simulation_performance column)."

            return evaluation
        except Exception as e:
            db.rollback()
            return f"Error evaluating response: {str(e)}"
        finally:
            db.close()
