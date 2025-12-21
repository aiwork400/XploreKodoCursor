"""
Tools for SupportAgent: Query life_in_japan_kb for legal/personal advice.
"""

from __future__ import annotations

from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.db_manager import LifeInJapanKB, SessionLocal


class GetLifeInJapanAdvice(BaseTool):
    """
    Query the life_in_japan_kb table for legal/personal advice about living in Japan.
    
    Searches by topic, category, or keywords to find relevant information.
    """

    query: str = Field(..., description="Search query - topic, category, or keywords (e.g., 'visa renewal', 'banking', 'healthcare')")
    category: Optional[str] = Field(
        default=None,
        description="Filter by category: 'legal', 'personal', 'financial', 'healthcare', 'housing'"
    )
    language: Optional[str] = Field(
        default="en",
        description="Preferred language for response: 'en', 'ja', 'ne'"
    )

    def run(self) -> str:
        """Query life_in_japan_kb and return relevant advice."""
        db: Session = SessionLocal()
        try:
            # Build query
            search_query = db.query(LifeInJapanKB)
            
            # Apply category filter if provided
            if self.category:
                search_query = search_query.filter(LifeInJapanKB.category == self.category)
            
            # Apply language filter
            if self.language:
                search_query = search_query.filter(LifeInJapanKB.language == self.language)
            
            # Search in topic, title, and content
            search_query = search_query.filter(
                or_(
                    LifeInJapanKB.topic.ilike(f"%{self.query}%"),
                    LifeInJapanKB.title.ilike(f"%{self.query}%"),
                    LifeInJapanKB.content.ilike(f"%{self.query}%")
                )
            )
            
            # Get results (limit to 5 most relevant)
            results = search_query.order_by(LifeInJapanKB.updated_at.desc()).limit(5).all()
            
            if not results:
                return f"❌ No information found for '{self.query}'. Please try different keywords or contact official sources for assistance."
            
            # Format results
            response = f"📚 Found {len(results)} result(s) for '{self.query}':\n\n"
            
            for i, result in enumerate(results, 1):
                response += f"**{i}. {result.title}**\n"
                response += f"   Category: {result.category or 'General'}\n"
                response += f"   Topic: {result.topic}\n"
                response += f"   \n{result.content[:500]}"
                if len(result.content) > 500:
                    response += "..."
                response += "\n\n"
                
                if result.source:
                    response += f"   Source: {result.source}\n\n"
            
            return response
            
        except Exception as e:
            return f"Error querying knowledge base: {str(e)}"
        finally:
            db.close()

