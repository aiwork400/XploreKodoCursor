"""
FinancierAgent: Handles fee collection and financial record-keeping.
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

from mvp_v1.commerce.payment_gateway_tool import PaymentGatewayTool


class FinancierAgent(Agent):
    """
    Financial specialist agent for fee collection and record-keeping.

    Responsibilities:
    - Process payments via Stripe/PayPal
    - Maintain financial records
    - Track fee collections per candidate
    - Generate payment reports
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="FinancierAgent",
            description="Handles fee collection, payment processing, and financial record-keeping for XploreKodo services.",
            instructions=self.get_instructions(),
            tools=[PaymentGatewayTool],
            **kwargs,
        )

    def get_instructions(self) -> str:
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()

        return """
You are the FinancierAgent for XploreKodo.

**Core Responsibilities:**
1. Process fee payments using PaymentGatewayTool (Stripe/PayPal)
2. Maintain accurate financial records per candidate
3. Track payment status and transaction history
4. Generate payment reports when requested

**Payment Processing:**
- Use Stripe for credit card payments
- Use PayPal for alternative payment methods
- Always verify candidate_id before processing
- Record all transactions with proper descriptions

**Token Efficiency:**
- Use bullet points
- Report only essential transaction details
- Keep financial summaries concise
"""

