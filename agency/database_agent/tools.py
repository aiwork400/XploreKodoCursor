"""
Database tools for DatabaseAgent to interact with PostgreSQL.
"""

from __future__ import annotations

from typing import Literal, Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy.orm import Session

from database.db_manager import Candidate, CurriculumProgress, SessionLocal


class QueryCandidates(BaseTool):
    """Query candidates from the database."""

    status: Optional[str] = Field(default=None, description="Filter by status (e.g., 'Travel-Ready', 'Incomplete')")
    track: Optional[str] = Field(default=None, description="Filter by track ('student' or 'jobseeker')")
    travel_ready: Optional[bool] = Field(default=None, description="Filter by travel_ready status")

    def run(self) -> str:
        """Query candidates with optional filters."""
        db: Session = SessionLocal()
        try:
            query = db.query(Candidate)
            
            if self.status:
                query = query.filter(Candidate.status == self.status)
            if self.track:
                query = query.filter(Candidate.track == self.track)
            if self.travel_ready is not None:
                query = query.filter(Candidate.travel_ready == self.travel_ready)
            
            candidates = query.all()
            
            if not candidates:
                return "No candidates found matching the criteria."
            
            result = f"Found {len(candidates)} candidate(s):\n\n"
            for candidate in candidates:
                result += f"- {candidate.candidate_id}: {candidate.full_name} ({candidate.track}) - Status: {candidate.status}, Travel-Ready: {candidate.travel_ready}\n"
            
            return result
        except Exception as e:
            return f"Error querying candidates: {str(e)}"
        finally:
            db.close()


class CreateCandidate(BaseTool):
    """Create a new candidate in the database."""

    candidate_id: str = Field(..., description="Unique candidate identifier")
    full_name: str = Field(..., description="Full legal name")
    track: str = Field(..., description="Candidate track: 'student' or 'jobseeker'")

    def run(self) -> str:
        """Create a new candidate record."""
        db: Session = SessionLocal()
        try:
            # Check if candidate already exists
            existing = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if existing:
                return f"Candidate {self.candidate_id} already exists."
            
            candidate = Candidate(
                candidate_id=self.candidate_id,
                full_name=self.full_name,
                track=self.track,
            )
            db.add(candidate)
            
            # Initialize curriculum progress
            curriculum = CurriculumProgress(candidate_id=self.candidate_id)
            db.add(curriculum)
            
            db.commit()
            
            return f"Successfully created candidate: {self.candidate_id} ({self.full_name})"
        except Exception as e:
            db.rollback()
            return f"Error creating candidate: {str(e)}"
        finally:
            db.close()


class UpdateCandidateStatus(BaseTool):
    """Update candidate status and travel_ready flag."""

    candidate_id: str = Field(..., description="Candidate identifier")
    status: Optional[str] = Field(default=None, description="New status")
    travel_ready: Optional[bool] = Field(default=None, description="Travel-ready flag")

    def run(self) -> str:
        """Update candidate status."""
        db: Session = SessionLocal()
        try:
            candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
            if not candidate:
                return f"Candidate {self.candidate_id} not found."
            
            if self.status:
                candidate.status = self.status
            if self.travel_ready is not None:
                candidate.travel_ready = self.travel_ready
            
            db.commit()
            
            updates = []
            if self.status:
                updates.append(f"status={self.status}")
            if self.travel_ready is not None:
                updates.append(f"travel_ready={self.travel_ready}")
            
            return f"Successfully updated candidate {self.candidate_id}: {', '.join(updates)}"
        except Exception as e:
            db.rollback()
            return f"Error updating candidate: {str(e)}"
        finally:
            db.close()


class UpdateCurriculumProgress(BaseTool):
    """Update curriculum progress for a candidate."""

    candidate_id: str = Field(..., description="Candidate identifier")
    
    # Language progress
    jlpt_level: Optional[Literal["N5", "N4", "N3"]] = Field(default=None, description="JLPT level to update")
    jlpt_units_completed: Optional[int] = Field(default=None, description="Number of units completed for the JLPT level")
    
    # Vocational progress
    vocational_module: Optional[Literal["kaigo_basics", "communication_skills", "physical_care"]] = Field(
        default=None, description="Vocational module to update"
    )
    vocational_lessons_completed: Optional[int] = Field(default=None, description="Number of lessons completed")

    def run(self) -> str:
        """Update curriculum progress in PostgreSQL."""
        db: Session = SessionLocal()
        try:
            # Get or create curriculum progress
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == self.candidate_id
            ).first()
            
            if not curriculum:
                # Create new curriculum progress
                curriculum = CurriculumProgress(candidate_id=self.candidate_id)
                db.add(curriculum)
            
            updates = []
            
            # Update JLPT progress
            if self.jlpt_level and self.jlpt_units_completed is not None:
                if self.jlpt_level == "N5":
                    curriculum.jlpt_n5_units_completed = self.jlpt_units_completed
                    updates.append(f"JLPT N5: {self.jlpt_units_completed}/{curriculum.jlpt_n5_total_units} units")
                elif self.jlpt_level == "N4":
                    curriculum.jlpt_n4_units_completed = self.jlpt_units_completed
                    updates.append(f"JLPT N4: {self.jlpt_units_completed}/{curriculum.jlpt_n4_total_units} units")
                elif self.jlpt_level == "N3":
                    curriculum.jlpt_n3_units_completed = self.jlpt_units_completed
                    updates.append(f"JLPT N3: {self.jlpt_units_completed}/{curriculum.jlpt_n3_total_units} units")
            
            # Update vocational progress
            if self.vocational_module and self.vocational_lessons_completed is not None:
                if self.vocational_module == "kaigo_basics":
                    curriculum.kaigo_basics_lessons_completed = self.vocational_lessons_completed
                    updates.append(f"Kaigo Basics: {self.vocational_lessons_completed}/{curriculum.kaigo_basics_total_lessons} lessons")
                elif self.vocational_module == "communication_skills":
                    curriculum.communication_skills_lessons_completed = self.vocational_lessons_completed
                    updates.append(f"Communication Skills: {self.vocational_lessons_completed}/{curriculum.communication_skills_total_lessons} lessons")
                elif self.vocational_module == "physical_care":
                    curriculum.physical_care_lessons_completed = self.vocational_lessons_completed
                    updates.append(f"Physical Care: {self.vocational_lessons_completed}/{curriculum.physical_care_total_lessons} lessons")
            
            if not updates:
                return "No updates specified. Provide jlpt_level/jlpt_units_completed or vocational_module/vocational_lessons_completed."
            
            db.commit()
            
            return f"Successfully updated curriculum progress for {self.candidate_id}:\n" + "\n".join(f"- {u}" for u in updates)
        except Exception as e:
            db.rollback()
            return f"Error updating curriculum progress: {str(e)}"
        finally:
            db.close()
