"""
CurriculumTracker for monitoring candidate progress across:
- Language: JLPT N5/N4/N3 units
- Vocational: Kaigo (Caregiving) technical modules
- Professional: AI & ML-relevant coaching modules

Includes Phase 2 AR-VR Classroom integration hooks (dormant).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import config


@dataclass
class LanguageProgress:
    """JLPT language learning progress."""

    level: str  # N5, N4, N3
    units_completed: int = 0
    total_units: int = 0
    last_updated: Optional[str] = None


@dataclass
class VocationalProgress:
    """Kaigo (Caregiving) vocational training progress."""

    module_name: str
    lessons_completed: int = 0
    total_lessons: int = 0
    certification_status: str = "In Progress"


@dataclass
class ProfessionalProgress:
    """AI & ML professional coaching progress."""

    module_name: str
    topics_completed: int = 0
    total_topics: int = 0
    project_status: str = "In Progress"


@dataclass
class CurriculumProgress:
    """Complete curriculum progress for a candidate."""

    candidate_id: str
    language: Dict[str, LanguageProgress] = field(default_factory=dict)
    vocational: List[VocationalProgress] = field(default_factory=list)
    professional: List[ProfessionalProgress] = field(default_factory=list)

    # Phase 2: AR-VR Classroom hooks (dormant)
    ar_vr_sessions_completed: int = 0
    ar_vr_last_session: Optional[str] = None


class CurriculumTracker:
    """
    Tracks candidate progress across Language, Vocational, and Professional modules.

    Phase 2: AR-VR Classroom integration hooks are present but dormant
    unless PHASE_2_ENABLED = True.
    """

    def __init__(self):
        self._progress: Dict[str, CurriculumProgress] = {}

    def initialize_candidate(self, candidate_id: str) -> None:
        """Initialize curriculum tracking for a new candidate."""
        if candidate_id not in self._progress:
            self._progress[candidate_id] = CurriculumProgress(candidate_id=candidate_id)

            # Initialize JLPT levels
            for level in ["N5", "N4", "N3"]:
                self._progress[candidate_id].language[level] = LanguageProgress(
                    level=level, total_units=self._get_total_units_for_level(level)
                )

            # Initialize Kaigo module
            self._progress[candidate_id].vocational.append(
                VocationalProgress(module_name="Kaigo Basics", total_lessons=20)
            )

            # Initialize AI/ML module
            self._progress[candidate_id].professional.append(
                ProfessionalProgress(module_name="AI/ML Fundamentals", total_topics=15)
            )

    def update_language_progress(
        self, candidate_id: str, level: str, units_completed: int
    ) -> None:
        """Update JLPT language learning progress."""
        if candidate_id not in self._progress:
            self.initialize_candidate(candidate_id)

        if level not in self._progress[candidate_id].language:
            self._progress[candidate_id].language[level] = LanguageProgress(
                level=level, total_units=self._get_total_units_for_level(level)
            )

        self._progress[candidate_id].language[level].units_completed = units_completed

    def update_vocational_progress(
        self, candidate_id: str, module_name: str, lessons_completed: int
    ) -> None:
        """Update Kaigo vocational training progress."""
        if candidate_id not in self._progress:
            self.initialize_candidate(candidate_id)

        # Find or create module
        module = next(
            (
                m
                for m in self._progress[candidate_id].vocational
                if m.module_name == module_name
            ),
            None,
        )
        if not module:
            module = VocationalProgress(module_name=module_name, total_lessons=20)
            self._progress[candidate_id].vocational.append(module)

        module.lessons_completed = lessons_completed

    def update_professional_progress(
        self, candidate_id: str, module_name: str, topics_completed: int
    ) -> None:
        """Update AI/ML professional coaching progress."""
        if candidate_id not in self._progress:
            self.initialize_candidate(candidate_id)

        # Find or create module
        module = next(
            (
                m
                for m in self._progress[candidate_id].professional
                if m.module_name == module_name
            ),
            None,
        )
        if not module:
            module = ProfessionalProgress(module_name=module_name, total_topics=15)
            self._progress[candidate_id].professional.append(module)

        module.topics_completed = topics_completed

    def get_progress(self, candidate_id: str) -> Optional[CurriculumProgress]:
        """Get complete curriculum progress for a candidate."""
        return self._progress.get(candidate_id)

    def record_ar_vr_session(self, candidate_id: str) -> None:
        """
        Record AR-VR Classroom session (Phase 2).

        Only functional if PHASE_2_ENABLED = True.
        """
        if not config.PHASE_2_ENABLED:
            raise RuntimeError(
                "AR-VR Classroom features are Phase 2. "
                "Set PHASE_2_ENABLED = True in config.py to activate."
            )

        if candidate_id not in self._progress:
            self.initialize_candidate(candidate_id)

        self._progress[candidate_id].ar_vr_sessions_completed += 1
        # In production, would store actual session timestamp
        self._progress[candidate_id].ar_vr_last_session = "2024-01-01T00:00:00Z"

    def _get_total_units_for_level(self, level: str) -> int:
        """Get total units for a JLPT level."""
        units_map = {"N5": 30, "N4": 40, "N3": 50}
        return units_map.get(level, 30)

