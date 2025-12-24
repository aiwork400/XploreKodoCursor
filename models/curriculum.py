"""
Curriculum Models for Triple-Track Coaching System

Defines the Syllabus model for managing video lessons across three tracks:
- Care-giving (Kaigo)
- Academic
- Tech (Food/Tech)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

# Use the same Base as db_manager for consistency
from database.db_manager import Base


class Syllabus(Base):
    """
    Syllabus table - manages video lessons and curriculum content.
    
    Supports Triple-Track Coaching:
    - Care-giving: Kaigo training videos
    - Academic: Academic preparation videos
    - Food/Tech: Technology and food industry training videos
    """

    __tablename__ = "syllabus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Track classification
    track = Column(
        String(50), 
        nullable=False, 
        index=True,
        comment="Track type: 'Care-giving', 'Academic', or 'Food/Tech'"
    )
    
    # Lesson metadata
    lesson_title = Column(String(500), nullable=False)
    lesson_description = Column(Text, nullable=True)
    lesson_number = Column(Integer, nullable=False, default=1)
    
    # Video file information
    video_path = Column(String(1000), nullable=False, comment="Relative path to video file in assets/videos/{track}/")
    video_filename = Column(String(500), nullable=False)
    
    # Language support (for multi-language video versions)
    language = Column(
        String(10), 
        nullable=False, 
        default="en",
        index=True,
        comment="Language code: 'en', 'ja', 'ne'"
    )
    
    # Topic for Socratic Assessment
    topic = Column(
        String(200), 
        nullable=True,
        comment="Topic identifier for triggering Socratic Assessment (e.g., 'omotenashi', 'knowledge_base')"
    )
    
    # Lesson metadata
    duration_minutes = Column(Integer, nullable=True, comment="Estimated video duration in minutes")
    difficulty_level = Column(String(20), nullable=True, comment="e.g., 'Beginner', 'Intermediate', 'Advanced'")
    
    # Ordering and organization
    module_name = Column(String(200), nullable=True, comment="Module or chapter name")
    sequence_order = Column(Integer, nullable=False, default=0, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<Syllabus(id={self.id}, track={self.track}, lesson_title={self.lesson_title}, language={self.language})>"

    def get_video_full_path(self) -> str:
        """Get the full path to the video file."""
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        return str(project_root / "assets" / "videos" / self.track.lower().replace("-", "_") / self.video_filename)

