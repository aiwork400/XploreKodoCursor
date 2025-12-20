# C:\Users\PC\SwarmMultiAgent\agency\architecture_agent\architecture_agent.py

from agency_swarm import Agent
from schemas.artifacts import ArchitectureBlueprint 
# NOTE: Make sure your schemas/artifacts.py file exists for this import to work!

class ArchitectureAgent(Agent):
    """
    The specialized system architect, responsible for translating high-level 
    requirements into structured, technical blueprints (ArchitectureBlueprint schema).
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="ArchitectureAgent",
            description="Designs the Pydantic models, component interfaces, and architectural blueprints (ArchitectureBlueprint) for the XploreKodo Platform.",
            instructions=self.get_instructions(),
            **kwargs
        )
        
    def get_instructions(self):
        return """
        You are the Architecture Agent. Your core output MUST be a JSON object that strictly conforms 
        to the 'ArchitectureBlueprint' Pydantic schema imported from 'schemas.artifacts'. 
        You must define all required PydanticModelDefinitions and ComponentInterfaces.
        """