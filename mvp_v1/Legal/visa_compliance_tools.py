"""
Tools for VisaComplianceAgent: Auto-compliance checking.
"""

from __future__ import annotations

from agency_swarm.tools import BaseTool
from pydantic import Field

from mvp_v1.Legal.compliance_checker import ComplianceChecker


class CheckCandidateCompliance(BaseTool):
    """
    Auto-compliance check tool for VisaComplianceAgent.

    Queries PostgreSQL database for candidate's full profile and automatically
    sets travel_ready and status if all requirements are met.
    """

    candidate_id: str = Field(..., description="Candidate identifier to check")

    def run(self) -> str:
        """
        Run auto-compliance check and update candidate status if compliant.

        Rules:
        - Student: 150-hour cert AND Financial Docs AND N5 Progress == 100% AND Fee Paid
        - Jobseeker: JLPT N4 AND Kaigo Test AND Fee Paid
        """
        return ComplianceChecker.auto_update_compliance(self.candidate_id)

