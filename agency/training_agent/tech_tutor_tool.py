"""
TechTutorTool: Explains AI/ML concepts using Japanese technical loanwords.

Specialized tool for teaching advanced AI/ML concepts from the knowledge_base
with emphasis on Japanese technical terminology (e.g., ニューラルネットワーク).
"""

from __future__ import annotations

import json
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy.orm import Session

import config
from database.db_manager import KnowledgeBase, SessionLocal

# Try to import google-genai for enhanced explanations
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class TechTutorTool(BaseTool):
    """
    Tech Tutor Tool for explaining AI/ML concepts using Japanese technical loanwords.
    
    Queries the knowledge_base for tech terms and provides explanations enriched with
    Japanese technical terminology (e.g., ニューラルネットワーク, 勾配降下法).
    """

    concept_name: str = Field(
        description="Name of the AI/ML concept to explain (e.g., 'Transformer Architecture', 'Gradient Descent')"
    )
    include_japanese_terms: bool = Field(
        default=True,
        description="Whether to emphasize Japanese technical loanwords in the explanation"
    )
    depth: str = Field(
        default="intermediate",
        description="Depth of explanation: 'basic', 'intermediate', or 'advanced'"
    )

    def run(self) -> str:
        """
        Explain an AI/ML concept using Japanese technical loanwords.
        
        Process:
        1. Query knowledge_base for the concept
        2. Extract Japanese technical terms
        3. Provide explanation with Japanese terminology emphasized
        4. Optionally use Gemini to enhance explanation
        """
        db: Session = SessionLocal()
        try:
            # Query knowledge_base for the concept
            kb_entry = db.query(KnowledgeBase).filter(
                KnowledgeBase.category == "tech",
                KnowledgeBase.concept_title.ilike(f"%{self.concept_name}%")
            ).first()
            
            if not kb_entry:
                # Try fuzzy search
                all_tech_terms = db.query(KnowledgeBase).filter(
                    KnowledgeBase.category == "tech"
                ).all()
                
                # Find closest match
                concept_lower = self.concept_name.lower()
                matches = [
                    term for term in all_tech_terms
                    if concept_lower in term.concept_title.lower() or
                    term.concept_title.lower() in concept_lower
                ]
                
                if matches:
                    kb_entry = matches[0]
                else:
                    # List available terms
                    available_terms = [term.concept_title for term in all_tech_terms]
                    return f"""❌ Concept "{self.concept_name}" not found in knowledge base.

📚 Available AI/ML Terms:
{chr(10).join(f"  • {term}" for term in available_terms[:10])}
{f"  ... and {len(available_terms) - 10} more" if len(available_terms) > 10 else ""}

💡 Tip: Use exact concept name from the list above."""
            
            # Extract content
            content = kb_entry.concept_content
            
            # Extract Japanese terms from content
            japanese_terms = self._extract_japanese_terms(content)
            
            # Build explanation
            explanation = f"""📖 **{kb_entry.concept_title}**

{content}

"""
            
            # Add Japanese terminology section if requested
            if self.include_japanese_terms and japanese_terms:
                explanation += "🇯🇵 **Japanese Technical Terms (技術用語):**\n\n"
                for term in japanese_terms:
                    explanation += f"  • {term}\n"
                explanation += "\n"
            
            # Enhance with Gemini if available and depth is advanced
            if GEMINI_AVAILABLE and self.depth == "advanced" and config.GEMINI_API_KEY:
                try:
                    enhanced = self._enhance_with_gemini(
                        concept=kb_entry.concept_title,
                        base_content=content,
                        japanese_terms=japanese_terms
                    )
                    if enhanced:
                        explanation += f"\n🤖 **Enhanced Explanation (AI-Generated):**\n\n{enhanced}\n"
                except Exception as e:
                    explanation += f"\n⚠️ Note: AI enhancement unavailable ({str(e)})\n"
            
            # Add learning tips based on depth
            if self.depth == "basic":
                explanation += "\n💡 **Learning Tip:** Start with understanding the core concept before diving into technical details.\n"
            elif self.depth == "intermediate":
                explanation += "\n💡 **Learning Tip:** Practice applying this concept in simple projects to reinforce understanding.\n"
            else:
                explanation += "\n💡 **Learning Tip:** Explore research papers and implement this concept from scratch for deep understanding.\n"
            
            return explanation
            
        except Exception as e:
            return f"❌ Error explaining concept: {str(e)}"
        finally:
            db.close()
    
    def _extract_japanese_terms(self, content: str) -> list[str]:
        """Extract Japanese terms (katakana/hiragana/kanji) from content."""
        import re
        
        # Pattern for Japanese characters (hiragana, katakana, kanji)
        japanese_pattern = r'[ひらがなカタカナ一-龯]+[ァ-ヶー]*'
        
        # Find all Japanese terms
        matches = re.findall(japanese_pattern, content)
        
        # Also look for terms in parentheses with Japanese
        paren_pattern = r'\(([^)]*[ひらがなカタカナ一-龯]+[ァ-ヶー]*[^)]*)\)'
        paren_matches = re.findall(paren_pattern, content)
        
        # Combine and deduplicate
        all_terms = list(set(matches + paren_matches))
        
        # Filter out very short matches (likely false positives)
        return [term for term in all_terms if len(term) >= 2]
    
    def _enhance_with_gemini(
        self,
        concept: str,
        base_content: str,
        japanese_terms: list[str]
    ) -> Optional[str]:
        """Enhance explanation using Gemini AI."""
        if not GEMINI_AVAILABLE or not config.GEMINI_API_KEY:
            return None
        
        try:
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            
            prompt = f"""You are a technical tutor explaining AI/ML concepts using Japanese technical loanwords.

Concept: {concept}

Base Content:
{base_content}

Japanese Technical Terms: {', '.join(japanese_terms)}

Provide an advanced explanation that:
1. Deepens understanding of the concept
2. Emphasizes the Japanese technical terminology
3. Explains how this concept relates to other AI/ML concepts
4. Provides practical applications or examples
5. Uses Japanese technical loanwords naturally in the explanation

Format the response in a clear, educational manner suitable for advanced learners."""

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Gemini enhancement error: {e}")
            return None


# For backward compatibility, also export as TechTutor
TechTutor = TechTutorTool

