"""
VREnvironmentAgent: Manages VR/AR scene states for immersive training.

Handles scene management for:
- Hospital Room (Kaigo training)
- Classroom (JLPT training)
- Other immersive environments
"""

from __future__ import annotations

from pathlib import Path

from agency_swarm import Agent

from agency.vr_environment_agent.tools import ManageVRScene


class VREnvironmentAgent(Agent):
    """
    VR/AR Environment specialist agent for managing immersive training scenes.

    Responsibilities:
    - Manage scene states (Hospital Room, Classroom, etc.)
    - Coordinate with TrainingAgent for immersive lessons
    - Handle scene transitions and state persistence
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="VREnvironmentAgent",
            description="Manages VR/AR scene states for immersive training environments. Handles Hospital Room (Kaigo) and Classroom (JLPT) scenes.",
            instructions=self.get_instructions(),
            tools=[ManageVRScene],
            **kwargs,
        )

    def get_instructions(self) -> str:
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()

        return """
You are the VREnvironmentAgent for XploreKodo.

**Core Responsibilities:**
1. Manage VR/AR scene states using ManageVRScene tool
2. Coordinate scene transitions for immersive training
3. Handle scene persistence and state management

**Scene Types:**
- **Hospital Room:** For Kaigo (caregiving) training simulations
- **Classroom:** For JLPT language learning with 3D Avatar Sensei
- **Other:** Future immersive environments

**Token Efficiency:**
- Use bullet points
- Report only essential scene state changes
- Keep scene descriptions concise
"""

