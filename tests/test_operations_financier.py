"""
TDD tests for OperationsAgent and FinancierAgent.

Verifies:
- GenerateWisdomReport tool functionality
- OperationsAgent initialization
- FinancierAgent initialization
"""

from __future__ import annotations

from agency.financier_agent.financier_agent import FinancierAgent
from agency.operations_agent.operations_agent import OperationsAgent
from agency.operations_agent.tools import GenerateWisdomReport


def test_generate_wisdom_report() -> None:
    """Verify GenerateWisdomReport tool generates structured report."""
    tool = GenerateWisdomReport(date="2024-01-01", include_token_metrics=True)
    result = tool.run()

    assert "XploreKodo Daily Wisdom Report" in result
    assert "Travel-Ready Status" in result
    assert "Advisory Agent Query Analysis" in result
    assert "System Health" in result
    assert "Token Thrift Optimization" in result
    assert "Recommendations" in result


def test_generate_wisdom_report_no_token_metrics() -> None:
    """Verify report can exclude token metrics."""
    tool = GenerateWisdomReport(include_token_metrics=False)
    result = tool.run()

    assert "Token Thrift Optimization" not in result


def test_operations_agent_initialization() -> None:
    """Verify OperationsAgent initializes correctly."""
    agent = OperationsAgent()

    assert agent.name == "OperationsAgent"
    assert len(agent.tools) > 0
    assert any("GenerateWisdomReport" in str(tool) for tool in agent.tools)


def test_financier_agent_initialization() -> None:
    """Verify FinancierAgent initializes correctly."""
    agent = FinancierAgent()

    assert agent.name == "FinancierAgent"
    assert len(agent.tools) > 0
    assert any("PaymentGatewayTool" in str(tool) for tool in agent.tools)

