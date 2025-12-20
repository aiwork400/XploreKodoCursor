"""
TrilingualTranslator tool for the AdvisoryAgent.

Handles translations between Nepali, Japanese, and English using config.TRILINGUAL_SUPPORT.
"""

from __future__ import annotations

from typing import Literal

from agency_swarm.tools import BaseTool
from pydantic import Field

import config


class TrilingualTranslator(BaseTool):
    """
    Translates text between Nepali, Japanese, and English.

    Uses the supported languages from config.TRILINGUAL_SUPPORT.
    """

    text: str = Field(..., description="Text to translate")
    source_language: Literal["Nepali", "Japanese", "English"] = Field(
        ..., description="Source language"
    )
    target_language: Literal["Nepali", "Japanese", "English"] = Field(
        ..., description="Target language"
    )

    def run(self) -> str:
        """
        Translate text between supported languages.

        Note: In production, this would integrate with a translation API
        (e.g., Google Translate, DeepL, or custom NLP model).
        For MVP, returns a structured response indicating translation intent.
        """
        # Validate languages are in supported list
        if self.source_language not in config.TRILINGUAL_SUPPORT:
            return f"✗ Source language '{self.source_language}' not in TRILINGUAL_SUPPORT: {config.TRILINGUAL_SUPPORT}"

        if self.target_language not in config.TRILINGUAL_SUPPORT:
            return f"✗ Target language '{self.target_language}' not in TRILINGUAL_SUPPORT: {config.TRILINGUAL_SUPPORT}"

        if self.source_language == self.target_language:
            return f"Source and target languages are the same. No translation needed."

        # MVP placeholder: In production, call translation API here
        # For now, return structured response
        return f"""
Translation Request:
- Source: {self.source_language}
- Target: {self.target_language}
- Text: {self.text[:100]}{'...' if len(self.text) > 100 else ''}

[Translation would be performed here via API integration]
"""


class AdvisoryQueryTool(BaseTool):
    """
    Query the AdvisoryKnowledgeBase for 'Life in Japan' troubleshooting information.
    """

    query: str = Field(..., description="Search query (topic, keyword, or tag)")
    search_type: Literal["topic", "keyword", "tag"] = Field(
        default="keyword", description="Type of search to perform"
    )

    def run(self) -> str:
        """
        Query the knowledge base and return relevant advisory content.

        Note: This tool requires access to AdvisoryKnowledgeBase instance.
        In production, this would be injected via agent context.
        """
        # MVP: Return structured response
        # In production, this would query the actual AdvisoryKnowledgeBase service
        return f"""
Advisory Query:
- Query: {self.query}
- Search Type: {self.search_type}

[Knowledge base lookup would be performed here]
[Results would include relevant 'Life in Japan' troubleshooting entries]
"""

