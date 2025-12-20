"""
Test script for Admin Notification System

Tests the Admin Monitoring Center by:
1. Inserting test events (Error and Warning) into activity_logs table
2. Validating that notifications appear in the Admin Dashboard
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from sqlalchemy.orm import Session
from database.db_manager import ActivityLog, SessionLocal, init_db
from utils.activity_logger import ActivityLogger


def test_insert_critical_error():
    """Insert a critical error event into activity_logs."""
    print("\n" + "=" * 70)
    print("🧪 Test 1: Inserting Critical Error Event")
    print("=" * 70)
    
    db: Session = SessionLocal()
    try:
        # Insert critical error: Speech-to-Text API Timeout
        error_log = ActivityLog(
            timestamp=datetime.now(timezone.utc),
            user_id="test_candidate_001",
            event_type="Error",
            severity="Error",
            message="Speech-to-Text API Timeout",
            event_metadata={
                "error_type": "API_Timeout",
                "service": "Google Cloud Speech-to-Text",
                "timeout_seconds": 30,
                "retry_count": 3,
                "candidate_id": "test_candidate_001",
                "audio_length_seconds": 5.2,
            }
        )
        
        db.add(error_log)
        db.commit()
        
        print("✅ Critical Error Event Inserted:")
        print(f"   Event Type: {error_log.event_type}")
        print(f"   Severity: {error_log.severity}")
        print(f"   Message: {error_log.message}")
        print(f"   User ID: {error_log.user_id}")
        print(f"   Timestamp: {error_log.timestamp}")
        print(f"   Metadata: {error_log.event_metadata}")
        
        return error_log.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to insert error event: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def test_insert_warning_event():
    """Insert a warning event into activity_logs."""
    print("\n" + "=" * 70)
    print("🧪 Test 2: Inserting Warning Event")
    print("=" * 70)
    
    db: Session = SessionLocal()
    try:
        # Insert warning: User failed same word 3 times
        warning_log = ActivityLog(
            timestamp=datetime.now(timezone.utc),
            user_id="test_candidate_001",
            event_type="Grading",
            severity="Warning",
            message="User Siddharth failed the same word 3 times",
            event_metadata={
                "word_title": "入浴",
                "word_id": 79,
                "failure_count": 3,
                "scores": [3, 4, 2],  # Last 3 attempts
                "candidate_name": "Siddharth",
                "recommendation": "Consider additional practice sessions for this word",
            }
        )
        
        db.add(warning_log)
        db.commit()
        
        print("✅ Warning Event Inserted:")
        print(f"   Event Type: {warning_log.event_type}")
        print(f"   Severity: {warning_log.severity}")
        print(f"   Message: {warning_log.message}")
        print(f"   User ID: {warning_log.user_id}")
        print(f"   Timestamp: {warning_log.timestamp}")
        print(f"   Metadata: {warning_log.event_metadata}")
        
        return warning_log.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to insert warning event: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def test_validate_notifications():
    """Validate that notifications can be retrieved."""
    print("\n" + "=" * 70)
    print("🧪 Test 3: Validating Notification Retrieval")
    print("=" * 70)
    
    try:
        # Get recent critical logs (last 1 hour)
        critical_logs = ActivityLogger.get_recent_critical_logs(hours=1)
        
        print(f"📊 Found {len(critical_logs)} critical event(s) in the last hour:")
        print()
        
        if critical_logs:
            for i, log in enumerate(critical_logs, 1):
                severity_icon = "🔴" if log.severity == "Error" else "🟡"
                print(f"{severity_icon} Event {i}:")
                print(f"   Type: {log.event_type}")
                print(f"   Severity: {log.severity}")
                print(f"   Message: {log.message}")
                print(f"   User ID: {log.user_id}")
                print(f"   Timestamp: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                if log.event_metadata:
                    print(f"   Metadata Keys: {list(log.event_metadata.keys())}")
                print()
        else:
            print("⚠️  No critical events found in the last hour.")
            print("   Note: Events may have been inserted more than 1 hour ago.")
        
        # Check for our specific test events
        error_found = False
        warning_found = False
        
        for log in critical_logs:
            if log.severity == "Error" and "Speech-to-Text API Timeout" in (log.message or ""):
                error_found = True
            if log.severity == "Warning" and "failed the same word 3 times" in (log.message or ""):
                warning_found = True
        
        print("=" * 70)
        print("✅ Validation Results:")
        print(f"   Error Event Found: {'✅ YES' if error_found else '❌ NO'}")
        print(f"   Warning Event Found: {'✅ YES' if warning_found else '❌ NO'}")
        
        if error_found and warning_found:
            print("\n🎉 All test events are present in the notification system!")
        else:
            print("\n⚠️  Some test events may not be visible (check timestamp - events must be < 1 hour old)")
        
        return error_found, warning_found
        
    except Exception as e:
        print(f"❌ Failed to validate notifications: {e}")
        import traceback
        traceback.print_exc()
        return False, False


def test_audit_log_retrieval():
    """Test retrieving audit logs."""
    print("\n" + "=" * 70)
    print("🧪 Test 4: Testing Audit Log Retrieval")
    print("=" * 70)
    
    try:
        # Get all audit logs
        audit_logs = ActivityLogger.get_audit_logs(limit=10)
        
        print(f"📋 Retrieved {len(audit_logs)} recent audit log entries:")
        print()
        
        for i, log in enumerate(audit_logs[:5], 1):  # Show first 5
            print(f"{i}. {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {log.event_type} ({log.severity})")
            print(f"   User: {log.user_id or 'System'}")
            print(f"   Message: {log.message or 'N/A'}")
            print()
        
        print("✅ Audit log retrieval working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Failed to retrieve audit logs: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("🧪 Admin Notification System Test Suite")
    print("=" * 70)
    
    # Ensure database table exists
    print("\n📋 Step 0: Ensuring activity_logs table exists...")
    try:
        init_db()  # This will create all tables including activity_logs if they don't exist
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize database: {e}")
        print("   Attempting to continue anyway...")
    
    # Test 1: Insert critical error
    error_id = test_insert_critical_error()
    
    # Test 2: Insert warning event
    warning_id = test_insert_warning_event()
    
    # Test 3: Validate notifications
    error_found, warning_found = test_validate_notifications()
    
    # Test 4: Test audit log retrieval
    audit_success = test_audit_log_retrieval()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"✅ Error Event Inserted: {'YES' if error_id else 'NO'} (ID: {error_id})")
    print(f"✅ Warning Event Inserted: {'YES' if warning_id else 'NO'} (ID: {warning_id})")
    print(f"✅ Error Event Visible: {'YES' if error_found else 'NO'}")
    print(f"✅ Warning Event Visible: {'YES' if warning_found else 'NO'}")
    print(f"✅ Audit Log Retrieval: {'YES' if audit_success else 'NO'}")
    print()
    
    if error_id and warning_id:
        print("🎉 Test events successfully inserted into activity_logs table!")
        print()
        print("📋 Next Steps:")
        print("   1. Open the Streamlit Dashboard")
        print("   2. Enable '🔒 Admin Mode' in the sidebar")
        print("   3. Check if the sidebar shows a notification count")
        print("   4. Go to 'Admin Dashboard' page")
        print("   5. Verify the two events appear in 'System Notifications' section")
        print()
        print("💡 Note: Events must be less than 1 hour old to appear in notifications.")
    else:
        print("❌ Some test events failed to insert. Check errors above.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()

