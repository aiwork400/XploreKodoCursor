# C:\Users\PC\SwarmMultiAgent\agency\ceo_agent\ceo_agent.py

from pathlib import Path
from agency_swarm import Agent

from agency.ceo_agent.CodebaseInspectorTool import CodebaseInspectorTool

class CEOAgent(Agent):
    """
    The CEO Agent is the main entry point for the user. Its primary role is to interpret 
    user requests, clarify ambiguous requirements, and delegate tasks to the God Agent.
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="CEOAgenrt",
            description="The central interface for the user. Interprets high-level requests and delegates all technical tasks to the God Agent. Uses the CodebaseInspectorTool.",
            instructions=self.get_instructions(),
            tools=[CodebaseInspectorTool()], # Assign the existing tool
            **kwargs
        )
        
    def get_instructions(self):
        """Load instructions from instructions.md file in the same directory."""
        instructions_path = Path(__file__).parent / "instructions.md"
        with open(instructions_path, "r", encoding="utf-8") as f:
            return f.read()