"""
Activity Logger Utility for Admin Monitoring Center.

Provides centralized logging for all agent actions and system events.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from database.db_manager import ActivityLog, SessionLocal


class ActivityLogger:
    """Centralized activity logger for system events."""

    @staticmethod
    def log(
        event_type: str,
        severity: str = "Info",
        user_id: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Log an activity to the activity_logs table.
        
        Args:
            event_type: Type of event (e.g., "Grading", "Briefing", "Error", "API_Call")
            severity: Severity level ("Info", "Warning", "Error")
            user_id: User/candidate ID associated with the event
            message: Human-readable message
            metadata: Additional JSON data (transcript, score, API response, etc.)
        
        Returns:
            True if logged successfully, False otherwise
        """
        db: Session = SessionLocal()
        try:
            log_entry = ActivityLog(
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                event_type=event_type,
                severity=severity,
                message=message,
                event_metadata=metadata or {},
            )
            
            db.add(log_entry)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            # Don't fail silently - at least print the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log activity: {e}")
            return False
        finally:
            db.close()

    @staticmethod
    def log_grading(
        candidate_id: str,
        word_title: str,
        score: int,
        transcript: Optional[str] = None,
        feedback: Optional[dict] = None,
    ) -> bool:
        """Log a grading event."""
        severity = "Warning" if score < 6 else "Info"
        message = f"Graded '{word_title}' for candidate {candidate_id}: {score}/10"
        
        metadata = {
            "word_title": word_title,
            "score": score,
            "transcript": transcript,
            "feedback": feedback,
        }
        
        return ActivityLogger.log(
            event_type="Grading",
            severity=severity,
            user_id=candidate_id,
            message=message,
            metadata=metadata,
        )

    @staticmethod
    def log_briefing(
        candidate_id: str,
        word_count: int,
        average_score: float,
    ) -> bool:
        """Log a briefing generation event."""
        message = f"Generated daily briefing for candidate {candidate_id}: {word_count} words, avg {average_score}/10"
        
        metadata = {
            "word_count": word_count,
            "average_score": average_score,
        }
        
        return ActivityLogger.log(
            event_type="Briefing",
            severity="Info",
            user_id=candidate_id,
            message=message,
            metadata=metadata,
        )

    @staticmethod
    def log_error(
        event_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        error_details: Optional[dict] = None,
    ) -> bool:
        """Log an error event."""
        metadata = {
            "error_message": error_message,
            "error_details": error_details or {},
        }
        
        return ActivityLogger.log(
            event_type=event_type,
            severity="Error",
            user_id=user_id,
            message=f"Error: {error_message}",
            metadata=metadata,
        )

    @staticmethod
    def log_api_call(
        api_name: str,
        status: str,
        latency_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        response_data: Optional[dict] = None,
    ) -> bool:
        """Log an API call event."""
        severity = "Warning" if latency_ms and latency_ms > 5000 else "Info"
        message = f"API call to {api_name}: {status}"
        if latency_ms:
            message += f" ({latency_ms:.0f}ms)"
        
        metadata = {
            "api_name": api_name,
            "status": status,
            "latency_ms": latency_ms,
            "response_data": response_data,
        }
        
        return ActivityLogger.log(
            event_type="API_Call",
            severity=severity,
            user_id=user_id,
            message=message,
            metadata=metadata,
        )

    @staticmethod
    def get_recent_critical_logs(hours: int = 1) -> list[ActivityLog]:
        """Get recent critical logs (Warning or Error) from the last N hours."""
        from datetime import timedelta
        
        db: Session = SessionLocal()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            logs = db.query(ActivityLog).filter(
                ActivityLog.timestamp >= cutoff_time,
                ActivityLog.severity.in_(["Warning", "Error"])
            ).order_by(ActivityLog.timestamp.desc()).all()
            
            return logs
        finally:
            db.close()

    @staticmethod
    def get_audit_logs(
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[ActivityLog]:
        """Get audit logs with optional filters."""
        db: Session = SessionLocal()
        try:
            query = db.query(ActivityLog)
            
            if user_id:
                query = query.filter(ActivityLog.user_id == user_id)
            if event_type:
                query = query.filter(ActivityLog.event_type == event_type)
            
            logs = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()
            return logs
        finally:
            db.close()

