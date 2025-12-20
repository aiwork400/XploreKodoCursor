"""
Simulation script to test Socratic questioning loop with Siddharth.

Automatically replies to the Agent's questions with 'slightly incorrect' answers
to test if the Socratic loop correctly provides hints instead of answers.
"""

from __future__ import annotations

import time
from pathlib import Path

import sys

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agency.training_agent.socratic_questioning_tool import SocraticQuestioningTool


class SiddharthSimulator:
    """
    Simulates Siddharth's responses to Socratic questions.
    
    Provides 'slightly incorrect' answers to test the Socratic loop.
    """

    def __init__(self, candidate_id: str = "siddharth_test"):
        self.candidate_id = candidate_id
        self.dialogue_count = 0
        self.max_dialogues = 5  # Limit to prevent infinite loops

    def generate_slightly_incorrect_answer(self, question_en: str) -> str:
        """
        Generate a 'slightly incorrect' answer based on the question.
        
        The answer should be partially correct but missing key elements,
        to test if the Socratic loop provides hints instead of answers.
        """
        question_lower = question_en.lower()
        
        # Pattern matching for different question types
        if "enter" in question_lower and "room" in question_lower:
            # Slightly incorrect: mentions greeting but not the specific Japanese way
            return "I should say hello to the patient."
        
        elif "uncomfortable" in question_lower or "pain" in question_lower:
            # Slightly incorrect: recognizes discomfort but doesn't mention indirect communication
            return "I would ask them if they are okay."
        
        elif "dignity" in question_lower or "privacy" in question_lower:
            # Slightly incorrect: understands concept but doesn't mention anticipatory service
            return "I should respect their privacy by closing the door."
        
        elif "personal space" in question_lower or "belongings" in question_lower:
            # Slightly incorrect: understands respect but doesn't mention asking permission
            return "I should be careful not to touch their things."
        
        elif "finish" in question_lower or "leaving" in question_lower:
            # Slightly incorrect: understands leaving but doesn't mention gratitude expression
            return "I should make sure everything is clean before I leave."
        
        elif "concept" in question_lower or "means" in question_lower:
            # For knowledge base questions - provide a partial understanding
            if "caregiving" in question_lower:
                return "I think it's about being polite and respectful to patients."
            else:
                return "I'm not entirely sure, but I think it's important for patient care."
        
        else:
            # Generic slightly incorrect answer
            return "I think I should be respectful and follow proper procedures."

    def simulate_dialogue(self, topic: str = "knowledge_base", start_new: bool = True):
        """
        Simulate a complete Socratic dialogue session.
        
        Args:
            topic: Topic for Socratic questioning ('knowledge_base' or 'omotenashi')
            start_new: If True, starts a new dialogue session
        """
        print("=" * 80)
        print("Siddharth Socratic Questioning Simulation")
        print("=" * 80)
        print(f"Candidate: {self.candidate_id}")
        print(f"Topic: {topic}")
        print(f"Strategy: Provide 'slightly incorrect' answers to test Socratic hints")
        print("=" * 80)
        print()

        # Start new session
        tool = SocraticQuestioningTool(
            candidate_id=self.candidate_id,
            topic=topic,
            start_new_session=start_new
        )

        question_result = tool.run()
        print("[AGENT] **Agent's Question:**")
        try:
            print(question_result)
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(question_result.encode('ascii', 'ignore').decode('ascii'))
        print()

        # Check if knowledge base is empty
        if "No concepts available" in question_result:
            print("[WARN] Knowledge base is empty. Please run:")
            print("   python database/extract_pdf_to_knowledge_base.py")
            print("\n[INFO] Falling back to predefined Omotenashi questions...")
            # Fallback to omotenashi
            tool = SocraticQuestioningTool(
                candidate_id=self.candidate_id,
                topic="omotenashi",
                start_new_session=start_new
            )
            question_result = tool.run()
            print("[AGENT] **Agent's Question (Omotenashi):**")
            try:
                print(question_result)
            except UnicodeEncodeError:
                # Fallback for Windows console encoding issues
                print(question_result.encode('ascii', 'ignore').decode('ascii'))
            print()

        # Extract question from result
        question_en = self._extract_question_from_result(question_result)

        # Simulate dialogue loop
        for i in range(self.max_dialogues):
            self.dialogue_count += 1
            
            # Generate slightly incorrect answer
            answer = self.generate_slightly_incorrect_answer(question_en)
            
            print(f"[SIDDHARTH] **Siddharth's Answer (Slightly Incorrect) #{self.dialogue_count}:**")
            print(f"{answer}")
            print()

            # Continue dialogue with Siddharth's answer
            tool = SocraticQuestioningTool(
                candidate_id=self.candidate_id,
                topic=topic,
                candidate_response=answer
            )

            next_result = tool.run()
            print("[AGENT] **Agent's Response:**")
            try:
                print(next_result)
            except UnicodeEncodeError:
                # Fallback for Windows console encoding issues
                print(next_result.encode('ascii', 'ignore').decode('ascii'))
            print()

            # Check if session is complete
            if "Congratulations" in next_result or "Session Complete" in next_result:
                print("[SUCCESS] **Simulation Complete:** Session finished successfully")
                break

            # Extract next question for continuation
            question_en = self._extract_question_from_result(next_result)
            
            if not question_en:
                print("[WARN] Could not extract next question. Ending simulation.")
                break

            # Small delay for readability
            time.sleep(1)

        print("=" * 80)
        print(f"Simulation Summary:")
        print(f"- Dialogues completed: {self.dialogue_count}")
        print(f"- Topic: {topic}")
        print("=" * 80)

    def _extract_question_from_result(self, result: str) -> str:
        """Extract the English question from the agent's result."""
        # Look for the English question section
        if "**🤔 Socratic Question (English):**" in result:
            lines = result.split("\n")
            in_question_section = False
            question_lines = []
            
            for line in lines:
                if "**🤔 Socratic Question (English):**" in line:
                    in_question_section = True
                    continue
                elif in_question_section:
                    if line.strip() and not line.startswith("**"):
                        question_lines.append(line.strip())
                    elif line.startswith("**") and question_lines:
                        break
            
            return " ".join(question_lines)
        
        # Fallback: look for question patterns
        lines = result.split("\n")
        for line in lines:
            if "?" in line and len(line) > 20:
                return line.strip()
        
        return ""


def main():
    """Main function to run the simulation."""
    simulator = SiddharthSimulator(candidate_id="siddharth_test")
    
    # Test with knowledge base (if available)
    print("Testing with knowledge base concepts...")
    simulator.simulate_dialogue(topic="knowledge_base", start_new=True)
    
    print("\n" + "=" * 80 + "\n")
    
    # Test with predefined Omotenashi questions
    print("Testing with predefined Omotenashi questions...")
    simulator.simulate_dialogue(topic="omotenashi", start_new=True)


if __name__ == "__main__":
    main()

