"""
AdvisoryAgent for handling candidate concerns and troubleshooting.

Provides trilingual advisory support for 'Life in Japan' scenarios.
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

import config
from mvp_v1.training.advisory_knowledge_base import AdvisoryKnowledgeBase
from mvp_v1.training.tools import AdvisoryQueryTool, TrilingualTranslator


class AdvisoryAgent(Agent):
    """
    Advisory specialist agent for candidate concerns and troubleshooting.

    Handles:
    - Trilingual translations (Nepali, Japanese, English)
    - 'Life in Japan' advisory queries
    - Phase 2 Voice-to-Voice logic (dormant unless PHASE_2_ENABLED)
    """

    def __init__(self, **kwargs):
        # Initialize knowledge base
        self.knowledge_base = AdvisoryKnowledgeBase()

        # Build tools list
        tools_list = [TrilingualTranslator, AdvisoryQueryTool]

        # Phase 2: Voice-to-Voice logic (dormant)
        if config.PHASE_2_ENABLED:
            # Placeholder for future Voice-to-Voice tool
            # from mvp_v1.training.tools import VoiceToVoiceTranslator
            # tools_list.append(VoiceToVoiceTranslator)
            pass

        super().__init__(
            name="AdvisoryAgent",
            description="Provides trilingual advisory support and troubleshooting guidance for candidates navigating life in Japan.",
            instructions=self.get_instructions(),
            tools=tools_list,
            **kwargs,
        )

    def get_instructions(self) -> str:
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()

        return """
You are the AdvisoryAgent for XploreKodo.

**Core Responsibilities:**
1. Provide trilingual translations (Nepali, Japanese, English) using TrilingualTranslator
2. Answer 'Life in Japan' troubleshooting queries using AdvisoryQueryTool
3. Support candidates with concerns about:
   - Ward Office registration
   - Understanding Japanese paychecks
   - Bank account opening
   - Health insurance
   - Other life-in-Japan topics

**Token Efficiency:**
- Use bullet points
- Provide concise, actionable answers
- Translate only when explicitly requested

**Phase 2 (Dormant):**
- Voice-to-Voice translation features are available only if PHASE_2_ENABLED=True
- Current mode: Text-based advisory only
"""

