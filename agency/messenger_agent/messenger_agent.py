"""
MessengerAgent: Handles candidate communications and notifications.
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

from agency.messenger_agent.tools import SendNotificationTool


class MessengerAgent(Agent):
    """
    Communication specialist agent for candidate notifications.

    Responsibilities:
    - Send notifications via Email, WhatsApp, SMS
    - Use trilingual templates for Travel-Ready messages
    - Automatically notify candidates when compliance checks pass
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="MessengerAgent",
            description="Handles candidate communications and notifications via Email, WhatsApp, and SMS. Supports trilingual messaging.",
            instructions=self.get_instructions(),
            tools=[SendNotificationTool],
            **kwargs,
        )

    def get_instructions(self) -> str:
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()

        return """
You are the MessengerAgent for XploreKodo.

**Core Responsibilities:**
1. Send notifications to candidates using SendNotificationTool
2. Use trilingual templates (Nepali, Japanese, English) for Travel-Ready messages
3. Automatically notify candidates when their status becomes 'Travel-Ready'
4. Support multiple channels: Email, WhatsApp, SMS

**Travel-Ready Notification:**
- When a candidate becomes Travel-Ready, send congratulatory messages in all three languages
- Use the trilingual template system to ensure consistent messaging
- Send via preferred channel (Email is default, WhatsApp/SMS if phone provided)

**Token Efficiency:**
- Use bullet points
- Report only essential notification details
- Keep messages concise but warm
"""

