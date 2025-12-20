"""
VisaComplianceAgent as agency-swarm Agent with auto-compliance tools.
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

from mvp_v1.Legal.visa_compliance_tools import CheckCandidateCompliance


class VisaComplianceAgent(Agent):
    """
    Visa & Compliance specialist agent with auto-compliance checking.

    Now includes CheckCandidateCompliance tool for automatic status updates.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="VisaComplianceAgent",
            description="Validates visa documents and ensures corridor-specific compliance. Includes auto-compliance checking that updates travel_ready and status automatically.",
            instructions=self.get_instructions(),
            tools=[CheckCandidateCompliance],
            **kwargs,
        )

    def get_instructions(self) -> str:
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()

        return """
You are the VisaComplianceAgent for XploreKodo.

**Core Responsibilities:**
1. Run auto-compliance checks using CheckCandidateCompliance tool
2. Enforce corridor-specific requirements (Japan, Europe, GCC)
3. Automatically update travel_ready and status when all requirements are met

**Auto-Compliance Rules:**
- **Student:** 150-hour cert AND Financial Docs AND N5 Progress == 100% AND Fee Paid
- **Jobseeker:** JLPT N4 AND Kaigo Test AND Fee Paid

**Token Efficiency:** Use bullet points. Report only compliance status and blockers.
"""

