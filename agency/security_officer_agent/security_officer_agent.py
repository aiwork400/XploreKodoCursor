# C:\Users\PC\SwarmMultiAgent\agency\security_officer_agent\security_officer_agent.py

from pathlib import Path

from agency_swarm import Agent
from schemas.reports import SecurityComplianceReport

from agency.security_officer_agent.tools import SecurityAuditTool


class SecurityOfficerAgent(Agent):
    """
    The Security Officer Agent acts as the Chief Information Security Officer (CISO)
    for the SACM, ensuring all artifacts meet stringent security and compliance policies 
    (OWASP, GDPR/CCPA, etc.).
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="SecurityOfficerAgent",
            description="Audits all designs and code for security vulnerabilities, policy violations (AuthN/AuthZ, data encryption), and general best practices. Includes SecurityAuditTool for checking .env files and hardcoded API keys.",
            instructions=self.get_instructions(),
            tools=[SecurityAuditTool],
            **kwargs,
        )
        
    def get_instructions(self):
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()
        
        return """
        You are the Security Officer Agent. You are the ultimate gatekeeper for security.

        1.  **Audit:** Receive code and blueprints from the God Agent and rigorously audit them against security guidelines (e.g., proper hash usage for passwords, input sanitization, secure session handling).
        2.  **Policy Enforcement:** Specifically check for correct implementation of authentication, authorization, and third-party payment gateway tokenization (Stripe/PayPal).
        3.  **SecurityAuditTool:** Use SecurityAuditTool to check for .env files being tracked and hardcoded API keys in mvp_v1/ directory.
        4.  **Reporting:** Your core output MUST be a JSON object conforming to the 'SecurityComplianceReport' schema. Report all findings, risk levels, and a final compliance status (Pass/Fail).
        5.  **Handoff:** Send the final report back to the God Agent.
        """