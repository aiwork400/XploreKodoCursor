"""
SupportAgent: Provides legal and personal advice for candidates living in Japan.

Pulls from life_in_japan_kb table to answer questions about:
- Visa renewal and immigration
- Banking and financial services
- Healthcare and insurance
- Housing and utilities
- Legal rights and responsibilities
"""

from agency.support_agent.support_agent import SupportAgent

__all__ = ["SupportAgent"]

