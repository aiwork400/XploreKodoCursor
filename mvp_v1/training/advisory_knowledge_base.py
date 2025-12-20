"""
AdvisoryKnowledgeBase service for 'Life in Japan' troubleshooting data.

Stores structured knowledge entries that can be queried by the AdvisoryAgent
to help candidates navigate life in Japan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AdvisoryEntry:
    """Single advisory knowledge entry."""

    topic: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)


class AdvisoryKnowledgeBase:
    """
    In-memory knowledge base for 'Life in Japan' advisory content.

    In production, this would be backed by a vector database or structured
    knowledge graph. For MVP, we use a simple in-memory dictionary.
    """

    def __init__(self):
        self._entries: Dict[str, AdvisoryEntry] = {}
        self._initialize_default_entries()

    def _initialize_default_entries(self) -> None:
        """Initialize with Phase 1 SOW-mandated troubleshooting topics."""

        # Ward Office Registration
        self.add_entry(
            AdvisoryEntry(
                topic="ward_office_registration",
                title="How to Register at a Ward Office (区役所)",
                content="""
                **Steps:**
                1. Bring your Residence Card (在留カード) and passport
                2. Visit your local Ward Office (区役所) within 14 days of arrival
                3. Fill out the 'Moving In Notification' (転入届)
                4. Receive your Certificate of Residence (住民票)
                
                **Required Documents:**
                - Residence Card
                - Passport
                - Proof of address (rental contract)
                
                **Important:** Registration is mandatory and must be done within 14 days.
                """,
                tags=["registration", "ward_office", "legal", "arrival"],
            )
        )

        # Understanding Japanese Paycheck
        self.add_entry(
            AdvisoryEntry(
                topic="japanese_paycheck",
                title="Understanding Your First Japanese Paycheck",
                content="""
                **Deductions Explained:**
                - **健康保険 (Health Insurance):** ~5% of salary
                - **厚生年金 (Pension):** ~9% of salary
                - **所得税 (Income Tax):** Progressive, starts at 5%
                - **住民税 (Resident Tax):** ~10% (charged in year 2)
                
                **Net vs Gross:**
                - Gross salary: Amount before deductions
                - Net salary: Amount you actually receive
                - Typical net: ~75-80% of gross for first year
                
                **Important:** Resident tax is NOT deducted in year 1, but you'll pay it in year 2.
                """,
                tags=["paycheck", "salary", "taxes", "deductions", "finance"],
            )
        )

        # Bank Account Opening
        self.add_entry(
            AdvisoryEntry(
                topic="bank_account_opening",
                title="Opening a Bank Account in Japan",
                content="""
                **Requirements:**
                - Residence Card (在留カード)
                - Proof of address (住民票)
                - Personal seal (印鑑) or signature
                
                **Recommended Banks:**
                - **Japan Post Bank (ゆうちょ銀行):** Most foreigner-friendly
                - **MUFG, Mizuho, SMBC:** Major banks, may require Japanese language
                
                **Process:**
                1. Visit bank branch with documents
                2. Fill application form (may need translation help)
                3. Receive cash card within 1-2 weeks
                
                **Note:** Some banks require 6+ months residency for full services.
                """,
                tags=["banking", "finance", "account", "setup"],
            )
        )

        # Health Insurance
        self.add_entry(
            AdvisoryEntry(
                topic="health_insurance",
                title="Health Insurance in Japan (国民健康保険)",
                content="""
                **Types:**
                - **Employee Insurance (健康保険):** If employed full-time
                - **National Health Insurance (国民健康保険):** If self-employed/student
                
                **Coverage:**
                - 70% coverage for medical expenses
                - You pay 30% at point of service
                
                **Registration:**
                - Automatic if employed
                - Must register at Ward Office if self-employed/student
                
                **Important:** Health insurance is mandatory. Failure to enroll can result in penalties.
                """,
                tags=["health", "insurance", "medical", "legal"],
            )
        )

        # Kaigo Caregiving Standards
        self.add_entry(
            AdvisoryEntry(
                topic="kaigo_medication_standards",
                title="Japanese Kaigo: Medication Administration Standards",
                content="""
                **Key Principles:**
                - Always verify patient identity before medication
                - Explain medication purpose clearly (use simple Japanese or gestures)
                - Check for allergies and contraindications
                - Document administration time and any reactions
                - Report refusals to supervisor immediately
                
                **Communication:**
                - Use calm, reassuring tone
                - Show medication clearly
                - Use visual aids if language barrier exists
                """,
                tags=["kaigo", "caregiving", "medication", "standards"],
            )
        )

        self.add_entry(
            AdvisoryEntry(
                topic="kaigo_fall_protocol",
                title="Japanese Kaigo: Patient Fall Response Protocol",
                content="""
                **Immediate Actions:**
                1. Assess patient safety - do NOT move if injury suspected
                2. Call for medical assistance immediately (119 in Japan)
                3. Stay with patient, provide comfort
                4. Document incident accurately
                
                **Prevention:**
                - Clear pathways
                - Proper lighting
                - Assistive devices when needed
                - Regular safety checks
                """,
                tags=["kaigo", "caregiving", "safety", "protocol", "standards"],
            )
        )

        self.add_entry(
            AdvisoryEntry(
                topic="kaigo_communication_standards",
                title="Japanese Kaigo: Communication with Non-Japanese Speakers",
                content="""
                **Strategies:**
                - Use simple gestures and visual aids
                - Translation apps for critical information
                - Involve interpreter when available
                - Learn basic Japanese caregiving phrases
                - Maintain patience and respect
                
                **Essential Phrases:**
                - 大丈夫ですか？(Daijoubu desu ka?) - Are you okay?
                - 痛いですか？(Itai desu ka?) - Does it hurt?
                - 手伝いましょうか？(Tetsudaimashou ka?) - Can I help you?
                """,
                tags=["kaigo", "caregiving", "communication", "standards"],
            )
        )

        self.add_entry(
            AdvisoryEntry(
                topic="kaigo_hygiene_standards",
                title="Japanese Kaigo: Personal Hygiene Assistance Standards",
                content="""
                **Key Principles:**
                - Maintain patient dignity at all times
                - Ensure privacy (close curtains, lock doors)
                - Use proper infection control techniques
                - Follow facility hygiene protocols
                - Document assistance provided
                
                **Techniques:**
                - Proper handwashing before/after
                - Use of gloves when appropriate
                - Respectful, gentle approach
                - Patient comfort as priority
                """,
                tags=["kaigo", "caregiving", "hygiene", "standards"],
            )
        )

    def add_entry(self, entry: AdvisoryEntry) -> None:
        """Add or update an advisory entry."""
        self._entries[entry.topic] = entry

    def get_entry(self, topic: str) -> Optional[AdvisoryEntry]:
        """Retrieve an advisory entry by topic."""
        return self._entries.get(topic)

    def search_by_tags(self, tags: List[str]) -> List[AdvisoryEntry]:
        """Search entries by tags (returns entries matching ANY tag)."""
        results = []
        for entry in self._entries.values():
            if any(tag in entry.tags for tag in tags):
                results.append(entry)
        return results

    def search_by_keyword(self, keyword: str) -> List[AdvisoryEntry]:
        """Search entries by keyword in title or content."""
        keyword_lower = keyword.lower()
        results = []
        for entry in self._entries.values():
            if (
                keyword_lower in entry.title.lower()
                or keyword_lower in entry.content.lower()
            ):
                results.append(entry)
        return results

    def list_all_topics(self) -> List[str]:
        """List all available topic keys."""
        return list(self._entries.keys())

