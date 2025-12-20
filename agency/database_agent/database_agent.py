# C:\Users\PC\SwarmMultiAgent\agency\database_agent\database_agent.py

from pathlib import Path

from agency_swarm import Agent

from agency.database_agent.tools import CreateCandidate, QueryCandidates, UpdateCandidateStatus, UpdateCurriculumProgress


class DatabaseAgent(Agent):
    """
    The Database Agent manages PostgreSQL 16 database operations for XploreKodo.

    Now uses real PostgreSQL database instead of in-memory lists.
    Handles candidate data, document vault, curriculum progress, and payments.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="DatabaseAgent",
            description="Manages PostgreSQL 16 database operations for XploreKodo. Handles candidates, documents, curriculum progress, and payments using SQLAlchemy ORM.",
            instructions=self.get_instructions(),
            tools=[QueryCandidates, CreateCandidate, UpdateCandidateStatus, UpdateCurriculumProgress],
            **kwargs,
        )
        
    def get_instructions(self):
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()
        
        return """
        You are the Database Agent for XploreKodo.

        **Core Responsibilities:**
        1. Manage PostgreSQL 16 database operations using SQLAlchemy ORM
        2. Query and update candidate records using QueryCandidates, CreateCandidate, UpdateCandidateStatus tools
        3. Ensure data integrity and proper relationships between tables
        4. Optimize queries for performance

        **Database Schema:**
        - candidates: Core candidate profiles
        - document_vault: Secure file path references
        - curriculum_progress: Learning progress tracking
        - payments: Payment transactions

        **Token Efficiency:**
        - Use bullet points
        - Report only essential query results
        - Keep responses concise
        """