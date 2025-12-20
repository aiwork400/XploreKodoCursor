"""
PaymentGatewayTool for Stripe and PayPal integration.

Handles fee collection for XploreKodo services with placeholder API keys.
"""

from __future__ import annotations

from typing import Literal, Optional

import config
from agency_swarm.tools import BaseTool
from pydantic import Field


class PaymentGatewayTool(BaseTool):
    """
    Processes payments via Stripe or PayPal.

    Note: API keys are placeholders. In production, these would be
    loaded from secure environment variables or a secrets manager.
    """

    amount: float = Field(..., description="Payment amount in USD")
    currency: str = Field(default="USD", description="Currency code (USD, JPY, etc.)")
    provider: Literal["stripe", "paypal"] = Field(..., description="Payment provider")
    candidate_id: str = Field(..., description="Candidate identifier for record-keeping")
    description: str = Field(default="", description="Payment description")

    # API keys loaded from config (which loads from .env)
    # These are not passed as tool parameters, but accessed from config module

    def run(self) -> str:
        """
        Process payment via selected provider.

        Returns structured response with transaction details.
        """
        if self.provider == "stripe":
            return self._process_stripe()
        elif self.provider == "paypal":
            return self._process_paypal()
        else:
            return f"✗ Unknown payment provider: {self.provider}"

    def _process_stripe(self) -> str:
        """Process payment via Stripe (placeholder)."""
        # In production: import stripe; stripe.api_key = config.STRIPE_API_KEY
        # charge = stripe.Charge.create(...)
        stripe_key = config.STRIPE_API_KEY or "sk_test_placeholder"
        return f"""
Stripe Payment Processed (Placeholder):
- Transaction ID: ch_stripe_placeholder_{self.candidate_id}
- Amount: {self.amount} {self.currency}
- Candidate: {self.candidate_id}
- Description: {self.description}
- Status: Success

[In production, this would call: stripe.Charge.create(...)]
"""

    def _process_paypal(self) -> str:
        """Process payment via PayPal (placeholder)."""
        # In production: Use PayPal SDK with config.PAYPAL_CLIENT_ID and config.PAYPAL_SECRET
        # payment = paypalrestsdk.Payment({...})
        paypal_client = config.PAYPAL_CLIENT_ID or "paypal_placeholder"
        return f"""
PayPal Payment Processed (Placeholder):
- Transaction ID: PAYPAL_placeholder_{self.candidate_id}
- Amount: {self.amount} {self.currency}
- Candidate: {self.candidate_id}
- Description: {self.description}
- Status: Success

[In production, this would call: paypalrestsdk.Payment.create(...)]
"""

