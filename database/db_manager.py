"""
Database Manager for PostgreSQL 16 using SQLAlchemy.

Manages connections and provides ORM models for:
- candidates
- document_vault
- curriculum_progress
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Database connection string - loaded from environment variables via config
import config

DATABASE_URL = config.DATABASE_URL

Base = declarative_base()


class Candidate(Base):
    """Candidates table - core candidate profile data."""

    __tablename__ = "candidates"

    candidate_id = Column(String(100), primary_key=True)
    full_name = Column(String(255), nullable=False)
    track = Column(String(20), nullable=False)  # 'student' or 'jobseeker'

    # Document paths
    passport_path = Column(String(500), nullable=True)
    coe_path = Column(String(500), nullable=True)
    transcripts_paths = Column(Text, nullable=True)  # JSON array as text

    # Student-specific requirements
    has_150_hour_study_certificate = Column(Boolean, default=False, nullable=False)
    has_financial_sponsor_docs = Column(Boolean, default=False, nullable=False)

    # Jobseeker-specific requirements
    has_jlpt_n4_or_n5 = Column(Boolean, default=False, nullable=False)
    has_kaigo_skills_test = Column(Boolean, default=False, nullable=False)

    # Status
    status = Column(String(50), default="Incomplete", nullable=False)
    travel_ready = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    documents = relationship("DocumentVault", back_populates="candidate", cascade="all, delete-orphan")
    curriculum = relationship("CurriculumProgress", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="candidate", cascade="all, delete-orphan")


class DocumentVault(Base):
    """Document vault table - secure file path references."""

    __tablename__ = "document_vault"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(100), ForeignKey("candidates.candidate_id"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # 'passport', 'coe', 'transcript', etc.
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    candidate = relationship("Candidate", back_populates="documents")


class CurriculumProgress(Base):
    """Curriculum progress table - tracks learning progress."""

    __tablename__ = "curriculum_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(100), ForeignKey("candidates.candidate_id"), unique=True, nullable=False)

    # Language progress (JLPT N5/N4/N3)
    jlpt_n5_units_completed = Column(Integer, default=0, nullable=False)
    jlpt_n5_total_units = Column(Integer, default=25, nullable=False)  # Updated to 25 units as specified
    jlpt_n4_units_completed = Column(Integer, default=0, nullable=False)
    jlpt_n4_total_units = Column(Integer, default=40, nullable=False)
    jlpt_n3_units_completed = Column(Integer, default=0, nullable=False)
    jlpt_n3_total_units = Column(Integer, default=50, nullable=False)

    # Vocational progress (Kaigo) - Detailed modules
    kaigo_basics_lessons_completed = Column(Integer, default=0, nullable=False)
    kaigo_basics_total_lessons = Column(Integer, default=8, nullable=False)
    communication_skills_lessons_completed = Column(Integer, default=0, nullable=False)
    communication_skills_total_lessons = Column(Integer, default=6, nullable=False)
    physical_care_lessons_completed = Column(Integer, default=0, nullable=False)
    physical_care_total_lessons = Column(Integer, default=6, nullable=False)
    kaigo_certification_status = Column(String(50), default="In Progress", nullable=False)

    # Professional progress (AI/ML)
    ai_ml_topics_completed = Column(Integer, default=0, nullable=False)
    ai_ml_total_topics = Column(Integer, default=15, nullable=False)
    ai_ml_project_status = Column(String(50), default="In Progress", nullable=False)

    # Phase 2: AR-VR hooks (dormant)
    ar_vr_sessions_completed = Column(Integer, default=0, nullable=False)
    ar_vr_last_session = Column(DateTime, nullable=True)

    # Kaigo Simulation Performance
    # Stored simulation scores: 'scenario_type:score;scenario_type:score'
    simulation_performance = Column(Text, nullable=True)

    # Socratic Dialogue History (JSONB)
    # Stores all Socratic questioning interactions: [{"question": {...}, "answer": "...", "timestamp": "..."}, ...]
    dialogue_history = Column(JSON, nullable=True)

    # Timestamps
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    candidate = relationship("Candidate", back_populates="curriculum")


class Payment(Base):
    """Payment transactions table - tracks fee collections."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(100), ForeignKey("candidates.candidate_id"), nullable=False)
    amount = Column(String(20), nullable=False)  # Store as string to preserve precision
    currency = Column(String(10), default="USD", nullable=False)
    provider = Column(String(20), nullable=False)  # 'stripe' or 'paypal'
    transaction_id = Column(String(255), nullable=False, unique=True)
    status = Column(String(50), default="pending", nullable=False)  # 'pending', 'success', 'failed'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship
    candidate = relationship("Candidate", back_populates="payments")


class KnowledgeBase(Base):
    """Knowledge base table - stores extracted content from caregiving training PDFs."""

    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(500), nullable=False)  # PDF file path
    concept_title = Column(String(500), nullable=False)  # Title/heading of the concept
    concept_content = Column(Text, nullable=False)  # Full text content
    page_number = Column(Integer, nullable=True)  # Page number in source PDF
    language = Column(String(10), default="ja", nullable=False)  # 'ja' for Japanese
    category = Column(String(100), nullable=True)  # e.g., 'grammar', 'vocabulary', 'caregiving'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Database session management
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables (use with caution)."""
    Base.metadata.drop_all(bind=engine)

