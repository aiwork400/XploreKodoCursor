"""
SupportAgent: Provides legal and personal advice for candidates living in Japan.

Uses life_in_japan_kb table to answer questions about visa, banking, healthcare, housing, etc.
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

from agency.support_agent.tools import GetLifeInJapanAdvice
from agency.support_agent.navigation_tool import NavigateToPage


class SupportAgent(Agent):
    """
    Support agent for providing legal and personal advice to candidates in Japan.
    
    Responsibilities:
    - Answer questions about visa renewal and immigration
    - Provide guidance on banking and financial services
    - Help with healthcare and insurance questions
    - Assist with housing and utilities
    - Explain legal rights and responsibilities
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="SupportAgent",
            description="Support agent providing legal and personal advice for candidates living in Japan. Uses life_in_japan_kb knowledge base to answer questions about visa, banking, healthcare, housing, and legal matters.",
            instructions=self.get_instructions(),
            tools=[
                GetLifeInJapanAdvice,
                NavigateToPage,
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
You are the SupportAgent for XploreKodo.

**Core Responsibilities:**
1. Answer questions about visa renewal and immigration procedures
2. Provide guidance on banking and financial services in Japan
3. Help with healthcare and insurance questions
4. Assist with housing and utilities information
5. Explain legal rights and responsibilities for foreign residents

**Knowledge Base:**
- Use GetLifeInJapanAdvice tool to query the life_in_japan_kb table
- Search by topic, category, or keywords
- Provide accurate, up-to-date information from the knowledge base

**Response Style:**
- Be clear, concise, and helpful
- Provide step-by-step guidance when applicable
- Include relevant links or resources if available
- If information is not in the knowledge base, acknowledge this and suggest contacting official sources

**Important:**
- Always verify information is current and accurate
- Direct candidates to official sources (immigration office, banks, etc.) for critical matters
- Maintain a supportive and empathetic tone
"""

