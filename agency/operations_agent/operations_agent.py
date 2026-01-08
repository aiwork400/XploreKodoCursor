"""
OperationsAgent: Platform troubleshooter and wisdom report generator.

Acts as the internal operations monitor for the XploreKodo platform.
"""

from __future__ import annotations

import os
from pathlib import Path

from agency_swarm import Agent

from agency.operations_agent.tools import GenerateWisdomReport


class OperationsAgent(Agent):
    """
    Operations specialist agent for platform health and wisdom reporting.

    Responsibilities:
    - Generate daily wisdom reports
    - Monitor system health
    - Track token optimization
    - Analyze troubleshooting patterns
    """

    def __init__(self, **kwargs):
        # Isolate OperationsAgent Knowledge Base: Use knowledge_base directory to avoid Windows File Lock
        # Default files_folder if not provided in kwargs
        if "files_folder" not in kwargs:
            # Replace the previous root path logic with knowledge_base directory
            project_root = Path(__file__).parent.parent.parent
            kb_path = os.path.join(project_root, 'knowledge_base')
            # Ensure the knowledge_base directory exists
            if not os.path.exists(kb_path):
                os.makedirs(kb_path)
            # Ensure the agent uses kb_path as its files_folder
            kwargs["files_folder"] = kb_path
        
        super().__init__(
            name="OperationsAgent",
            description="Platform troubleshooter and operations monitor. Generates wisdom reports and tracks system health for XploreKodo.",
            instructions=self.get_instructions(),
            tools=[GenerateWisdomReport],
            **kwargs,
        )

    def get_instructions(self) -> str:
        """Load instructions from instructions.md if it exists, otherwise return inline instructions."""
        instructions_path = Path(__file__).parent / "instructions.md"
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read()

        return """
You are the OperationsAgent for XploreKodo.

**Core Responsibilities:**
1. Generate daily wisdom reports using GenerateWisdomReport tool
2. Monitor platform health and system status
3. Track token usage and optimization opportunities
4. Analyze patterns in candidate queries and troubleshooting requests
5. Provide actionable recommendations for platform improvement
6. **Analyze Manifesto and Save to Wisdom Hub** - When requested, generate comprehensive wisdom reports

**Wisdom Report Generation:**
- When you receive a request to "Analyze Manifesto and Save to Wisdom Hub" or generate a wisdom report:
  - Use the GenerateWisdomReport tool immediately
  - The tool will automatically save the report to: operations/reports/wisdom_report_YYYY_MM_DD.md
  - This is the exact directory the Wisdom Hub scans for reports
  - Reports are saved in Markdown format and will appear in the Wisdom Hub dashboard

**Manifesto Access:**
- The Manifesto file is located at: Xplora_Kodo_Manifesto.md (in your files_folder which is the knowledge_base directory)
- You have access to the knowledge_base directory through your files_folder configuration
- When generating reports, reference the Manifesto to ensure strategic alignment with Xplora Kodo's foundational principles
- The Manifesto contains the Mission Statement, Triple-Track Coaching System, and core platform values
- Access files in knowledge_base using relative paths from your files_folder (e.g., "Xplora_Kodo_Manifesto.md")

**Token Efficiency:**
- Use bullet points
- Focus on metrics and actionable insights
- Keep reports concise but comprehensive

**Wisdom Report Contents:**
- Travel-Ready candidate counts
- Common troubleshooting queries
- System health metrics
- Token thrift optimization status
- Actionable recommendations
- Platform manifesto analysis (when requested)

**Path Verification:**
- Reports are saved to: operations/reports/wisdom_report_*.md
- The Wisdom Hub reads from this exact location
- Always use the GenerateWisdomReport tool - it handles the correct path automatically
"""

