"""Database module for PostgreSQL 16 integration."""

from database.db_manager import (
    Base,
    Candidate,
    CurriculumProgress,
    DocumentVault,
    Payment,
    SessionLocal,
    get_db,
    init_db,
)

__all__ = [
    "Base",
    "Candidate",
    "DocumentVault",
    "CurriculumProgress",
    "Payment",
    "SessionLocal",
    "get_db",
    "init_db",
]

