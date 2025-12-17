# C:\Users\PC\SwarmMultiAgent\agency\god_agent\god_agent.py

from pathlib import Path
from agency_swarm import Agent
from agency_swarm.tools import BaseTool

class GodAgent(Agent):
    """
    The God Agent serves as the internal Project Manager and quality control layer 
    for the SACM (System Architecture Control Module).
    
    Responsibilities:
    1.  Receives high-level tasks from the CEO.
    2.  Validates and routes the task to the appropriate specialized agent (e.g., Architecture Agent).
    3.  Receives structured output (like an ArchitectureBlueprint) from specialized agents.
    4.  Performs preliminary validation of the structured output against the SACM rules.
    5.  Routes validated output to the next agent in the sequence (e.g., Developer Agent).
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="GodAgent",
            description="The chief orchestration agent and Project Manager for all SACM development tasks. Ensures compliance and manages the flow from design to implementation.",
            instructions=self.get_instructions(),
            **kwargs
        )
        
    def get_instructions(self):
        """Load instructions from instructions.md file in the same directory."""
        instructions_path = Path(__file__).parent / "instructions.md"
        with open(instructions_path, "r", encoding="utf-8") as f:
            return f.read()