# FIX: Import Agent explicitly from agency_swarm.agent.core
from agency_swarm import Agent 
from .tools.document_vault import LoadArtifacts, OffloadArtifacts

class DocumentVaultAgent(Agent):
    def __init__(self):
        super().__init__(
            name="DocumentVaultAgent",
            description="The specialized agent for managing the Document Vault.",
            instructions="./instructions.md",
            tools=[LoadArtifacts, OffloadArtifacts],
        )