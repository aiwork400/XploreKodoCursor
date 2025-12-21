"""
Test SupportAgent Knowledge Base Retrieval

Verifies that SupportAgent can successfully retrieve Life-in-Japan tips.
"""

from __future__ import annotations

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agency.support_agent.tools import GetLifeInJapanAdvice


def test_support_agent_queries():
    """Test SupportAgent queries for each core category."""
    print("=" * 80)
    print("🧪 Testing SupportAgent Knowledge Base Retrieval")
    print("=" * 80)
    
    test_queries = [
        ("SSW rights", "legal", "Testing Legal category"),
        ("Japan Post Bank", "financial", "Testing Finance category"),
        ("Transitioning from Student", "visa", "Testing Visa category"),
        ("Shikikin", "housing", "Testing Housing category"),
        ("Medical emergency", "emergency", "Testing Emergency category"),
    ]
    
    all_passed = True
    
    for query, category, description in test_queries:
        print(f"\n{'=' * 80}")
        print(f"📋 {description}")
        print(f"   Query: '{query}' | Category: {category}")
        print(f"{'=' * 80}")
        
        try:
            tool = GetLifeInJapanAdvice(
                query=query,
                category=category,
                language="en"
            )
            
            result = tool.run()
            
            if "❌ No information found" in result:
                print(f"❌ FAILED: No results found for '{query}'")
                all_passed = False
            else:
                print(f"✅ SUCCESS: Found information")
                print(f"\n{result[:500]}...")  # Show first 500 chars
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 All SupportAgent tests PASSED!")
    else:
        print("⚠️  Some tests FAILED. Please check the results above.")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = test_support_agent_queries()
    sys.exit(0 if success else 1)

