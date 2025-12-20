"""
Tools for MessengerAgent: Notification sending via Email, WhatsApp, SMS.
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

import config
from mvp_v1.notifications.templates import NotificationTemplates


class SendNotificationTool(BaseTool):
    """
    Sends notifications to candidates via Email, WhatsApp, or SMS.

    Supports:
    - Email (SMTP/SendGrid placeholder)
    - WhatsApp/SMS (Twilio placeholder)
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    candidate_name: str = Field(..., description="Candidate full name")
    candidate_email: str = Field(..., description="Candidate email address")
    candidate_phone: Optional[str] = Field(default=None, description="Candidate phone number (for WhatsApp/SMS)")
    notification_type: Literal["email", "whatsapp", "sms"] = Field(..., description="Notification channel")
    message_type: Literal["travel_ready", "status_update", "custom"] = Field(
        default="travel_ready", description="Type of notification message"
    )
    custom_message: Optional[str] = Field(default=None, description="Custom message (if message_type='custom')")
    language: Literal["Nepali", "Japanese", "English"] = Field(
        default="English", description="Message language"
    )

    def run(self) -> str:
        """
        Send notification via selected channel.

        In production, this would integrate with:
        - SendGrid/SMTP for emails
        - Twilio for WhatsApp/SMS
        """
        # Get message content
        if self.message_type == "travel_ready":
            messages = NotificationTemplates.get_travel_ready_message(self.candidate_name)
            message = messages.get(self.language, messages["English"])
        elif self.message_type == "custom" and self.custom_message:
            message = self.custom_message
        else:
            message = f"Status update for {self.candidate_name}"

        # API keys loaded from config (which loads from .env)
        if self.notification_type == "email":
            return self._send_email(message)
        elif self.notification_type == "whatsapp":
            return self._send_whatsapp(message)
        elif self.notification_type == "sms":
            return self._send_sms(message)
        else:
            return f"✗ Unknown notification type: {self.notification_type}"

    def _send_email(self, message: str) -> str:
        """Send email via SMTP/SendGrid (placeholder)."""
        # In production: Use SendGrid API or SMTP
        # sendgrid_api_key = config.SENDGRID_API_KEY
        # sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
        # ...
        sendgrid_key = config.SENDGRID_API_KEY or "sendgrid_placeholder"
        return f"""
Email Notification Sent (Placeholder):
- To: {self.candidate_email}
- Subject: XploreKodo - {self.message_type.replace('_', ' ').title()}
- Language: {self.language}
- Message: {message[:100]}...

[In production, this would call: sendgrid.SendGridAPIClient(...)]
"""

    def _send_whatsapp(self, message: str) -> str:
        """Send WhatsApp message via Twilio (placeholder)."""
        # In production: Use Twilio API with config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN
        # client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        # ...
        twilio_sid = config.TWILIO_ACCOUNT_SID or "twilio_placeholder"
        return f"""
WhatsApp Notification Sent (Placeholder):
- To: {self.candidate_phone}
- Language: {self.language}
- Message: {message[:100]}...

[In production, this would call: twilio.Client(...)]
"""

    def _send_sms(self, message: str) -> str:
        """Send SMS via Twilio (placeholder)."""
        # In production: Use Twilio API with config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN
        twilio_sid = config.TWILIO_ACCOUNT_SID or "twilio_placeholder"
        return f"""
SMS Notification Sent (Placeholder):
- To: {self.candidate_phone}
- Language: {self.language}
- Message: {message[:100]}...

[In production, this would call: twilio.Client(...)]
"""

