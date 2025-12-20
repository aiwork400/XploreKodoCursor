"""
TDD tests for Trilingual Advisor Engine.

Verifies:
- TrilingualTranslator tool functionality
- AdvisoryKnowledgeBase service
- AdvisoryAgent integration
- Phase 2 Voice-to-Voice remains dormant
"""

from __future__ import annotations

import pytest

import config
from mvp_v1.training.advisory_knowledge_base import AdvisoryKnowledgeBase, AdvisoryEntry
from mvp_v1.training.tools import AdvisoryQueryTool, TrilingualTranslator


def test_trilingual_translator_validates_languages() -> None:
    """Verify TrilingualTranslator validates against config.TRILINGUAL_SUPPORT."""
    translator = TrilingualTranslator(
        text="Hello",
        source_language="English",
        target_language="Japanese",
    )
    result = translator.run()
    assert "Translation Request" in result
    assert "English" in result
    assert "Japanese" in result


def test_trilingual_translator_rejects_unsupported_language() -> None:
    """Verify translator rejects languages not in TRILINGUAL_SUPPORT."""
    translator = TrilingualTranslator(
        text="Hello",
        source_language="French",  # Not in TRILINGUAL_SUPPORT
        target_language="English",
    )
    result = translator.run()
    assert "not in TRILINGUAL_SUPPORT" in result


def test_advisory_knowledge_base_initialization() -> None:
    """Verify AdvisoryKnowledgeBase initializes with default entries."""
    kb = AdvisoryKnowledgeBase()
    
    # Check default entries exist
    assert kb.get_entry("ward_office_registration") is not None
    assert kb.get_entry("japanese_paycheck") is not None
    assert kb.get_entry("bank_account_opening") is not None
    assert kb.get_entry("health_insurance") is not None


def test_advisory_knowledge_base_search_by_tags() -> None:
    """Verify knowledge base can search entries by tags."""
    kb = AdvisoryKnowledgeBase()
    
    # Search for finance-related entries
    results = kb.search_by_tags(["finance", "paycheck"])
    assert len(results) > 0
    
    # Verify results contain expected topics
    topics = [entry.topic for entry in results]
    assert "japanese_paycheck" in topics or "bank_account_opening" in topics


def test_advisory_knowledge_base_search_by_keyword() -> None:
    """Verify knowledge base can search entries by keyword."""
    kb = AdvisoryKnowledgeBase()
    
    # Search for "ward" keyword
    results = kb.search_by_keyword("ward")
    assert len(results) > 0
    assert any("ward" in entry.title.lower() or "ward" in entry.content.lower() for entry in results)


def test_advisory_query_tool_structure() -> None:
    """Verify AdvisoryQueryTool returns structured response."""
    tool = AdvisoryQueryTool(
        query="ward office registration",
        search_type="keyword",
    )
    result = tool.run()
    assert "Advisory Query" in result
    assert "ward office registration" in result


def test_phase_2_voice_to_voice_dormant() -> None:
    """Verify Phase 2 Voice-to-Voice remains dormant when PHASE_2_ENABLED=False."""
    # Ensure flag is False
    assert config.PHASE_2_ENABLED is False
    
    # Attempting to import should not raise, but using it should
    try:
        from mvp_v1.training.voice_to_voice import VoiceToVoiceTranslator
        
        # Attempting to instantiate should raise RuntimeError
        with pytest.raises(RuntimeError, match="Phase 2 feature"):
            VoiceToVoiceTranslator()
    except ImportError:
        # If import fails, that's also acceptable (module may not be structured that way)
        pass


def test_advisory_agent_initialization() -> None:
    """Verify AdvisoryAgent can be instantiated with correct tools."""
    from mvp_v1.training.advisory_agent import AdvisoryAgent
    
    agent = AdvisoryAgent()
    
    # Verify agent has correct name
    assert agent.name == "AdvisoryAgent"
    
    # Verify tools are present
    tool_names = [tool.__name__ if hasattr(tool, "__name__") else str(tool) for tool in agent.tools]
    assert "TrilingualTranslator" in str(tool_names) or any("TrilingualTranslator" in str(t) for t in agent.tools)
    assert "AdvisoryQueryTool" in str(tool_names) or any("AdvisoryQueryTool" in str(t) for t in agent.tools)

