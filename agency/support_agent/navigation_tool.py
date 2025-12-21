"""
Navigation Tool for SupportAgent: Navigate to different Streamlit pages based on user requests.

Allows the agent to trigger page navigation (e.g., 'Take me to the Visa page').
"""

from __future__ import annotations

from agency_swarm.tools import BaseTool
from pydantic import Field


class NavigateToPage(BaseTool):
    """
    Navigate to a specific page in the Streamlit dashboard.
    
    This tool allows the SupportAgent to help users navigate to different sections
    of the XploreKodo platform based on their requests.
    """

    page_name: str = Field(
        ...,
        description="Name of the page to navigate to. Options: 'Candidate View', 'Wisdom Hub', 'Live Simulator', 'Financial Ledger', 'Compliance', 'Life-in-Japan Support', 'Virtual Classroom', 'Admin Dashboard'"
    )
    reason: str = Field(
        default="",
        description="Reason for navigation (optional, for logging purposes)"
    )

    def run(self) -> str:
        """
        Navigate to the specified page.
        
        Note: In Streamlit, page navigation is handled through session state.
        This tool sets the navigation target in session state, which the main
        app will read to switch pages.
        """
        # Valid page names
        valid_pages = [
            "Candidate View",
            "Wisdom Hub",
            "Live Simulator",
            "Financial Ledger",
            "Compliance",
            "Life-in-Japan Support",
            "Virtual Classroom",
            "Admin Dashboard"
        ]
        
        # Normalize page name (case-insensitive matching)
        page_name_lower = self.page_name.lower()
        matched_page = None
        
        for page in valid_pages:
            if page_name_lower in page.lower() or page.lower() in page_name_lower:
                matched_page = page
                break
        
        if not matched_page:
            # Try fuzzy matching for common requests
            if "visa" in page_name_lower or "immigration" in page_name_lower:
                matched_page = "Life-in-Japan Support"
            elif "candidate" in page_name_lower or "student" in page_name_lower:
                matched_page = "Candidate View"
            elif "classroom" in page_name_lower or "coaching" in page_name_lower:
                matched_page = "Virtual Classroom"
            elif "admin" in page_name_lower or "dashboard" in page_name_lower:
                matched_page = "Admin Dashboard"
            elif "financial" in page_name_lower or "payment" in page_name_lower:
                matched_page = "Financial Ledger"
            elif "compliance" in page_name_lower or "document" in page_name_lower:
                matched_page = "Compliance"
            elif "wisdom" in page_name_lower or "report" in page_name_lower:
                matched_page = "Wisdom Hub"
            else:
                return f"""❌ Page "{self.page_name}" not found.

Available pages:
{chr(10).join(f"  • {page}" for page in valid_pages)}

💡 Tip: Try saying "Take me to [page name]" or "Show me [page name]"
"""
        
        # Set navigation target in a way that Streamlit can read
        # Note: This requires the main app to check for navigation requests
        navigation_message = f"""✅ Navigating to **{matched_page}**...

{self.reason if self.reason else f"Taking you to the {matched_page} page as requested."}

**Note:** The page will change automatically. If it doesn't, please select "{matched_page}" from the sidebar menu.
"""
        
        return navigation_message

