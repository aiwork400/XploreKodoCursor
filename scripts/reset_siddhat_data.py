"""
Manual Data Reset Script for Student Siddhat

This script:
1. Connects to PostgreSQL and deletes all data for Siddhat
2. Resets user_progress.json for Siddhat profile
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from database.db_manager import SessionLocal, Candidate, CurriculumProgress, StudentPerformance
from sqlalchemy import or_

def reset_siddhat_postgresql():
    """Delete all PostgreSQL data for Siddhat."""
    db = SessionLocal()
    try:
        # Find candidate_id for Siddhat (search by name containing "Siddhat" or "Siddharth")
        candidates = db.query(Candidate).filter(
            or_(
                Candidate.full_name.ilike('%Siddhat%'),
                Candidate.full_name.ilike('%Siddharth%')
            )
        ).all()
        
        if not candidates:
            print("[WARNING] No candidate found with name containing 'Siddhat' or 'Siddharth'")
            print("   Searching for exact match 'Siddhat'...")
            # Try exact match
            candidate = db.query(Candidate).filter(
                Candidate.candidate_id == 'Siddhat'
            ).first()
            if candidate:
                candidates = [candidate]
            else:
                print("[ERROR] No candidate found. Please check the candidate_id or full_name.")
                return False
        
        deleted_count = 0
        for candidate in candidates:
            candidate_id = candidate.candidate_id
            print(f"\n[INFO] Found candidate: {candidate.full_name} (ID: {candidate_id})")
            
            # Delete from StudentPerformance (lesson history equivalent)
            perf_records = db.query(StudentPerformance).filter(
                StudentPerformance.candidate_id == candidate_id
            ).all()
            perf_count = len(perf_records)
            if perf_count > 0:
                db.query(StudentPerformance).filter(
                    StudentPerformance.candidate_id == candidate_id
                ).delete()
                print(f"   [OK] Deleted {perf_count} records from student_performance table")
                deleted_count += perf_count
            
            # Reset mastery_scores in CurriculumProgress
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == candidate_id
            ).first()
            if curriculum:
                if curriculum.mastery_scores:
                    print(f"   [OK] Resetting mastery_scores in curriculum_progress")
                    curriculum.mastery_scores = None
                    deleted_count += 1
                # Also reset dialogue_history if it exists
                if curriculum.dialogue_history:
                    print(f"   [OK] Resetting dialogue_history in curriculum_progress")
                    curriculum.dialogue_history = None
                    deleted_count += 1
        
        db.commit()
        print(f"\n[SUCCESS] PostgreSQL reset complete. Deleted/reset {deleted_count} items.")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error resetting PostgreSQL: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def reset_siddhat_json():
    """Reset user_progress.json for Siddhat."""
    json_path = project_root / "assets" / "user_progress.json"
    
    if not json_path.exists():
        print(f"[WARNING] user_progress.json not found at {json_path}")
        return False
    
    try:
        # Read current JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reset lesson_history to empty array
        if 'lesson_history' in data:
            original_count = len(data['lesson_history'])
            data['lesson_history'] = []
            print(f"   [OK] Cleared {original_count} entries from lesson_history")
        
        # Reset track_mastery to 0.0 for all tracks
        if 'track_mastery' in data:
            for track in data['track_mastery']:
                if isinstance(data['track_mastery'][track], dict):
                    for skill in data['track_mastery'][track]:
                        data['track_mastery'][track][skill] = 0.0
            print(f"   [OK] Reset all track_mastery scores to 0.0")
        
        # Reset total_word_count
        if 'total_word_count' in data:
            data['total_word_count'] = 0
            print(f"   [OK] Reset total_word_count to 0")
        
        # Reset sessions
        if 'sessions' in data:
            original_sessions = len(data['sessions'])
            data['sessions'] = {}
            print(f"   [OK] Cleared {original_sessions} sessions")
        
        # Write back to file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"\n[SUCCESS] JSON reset complete.")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error resetting JSON: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main reset function."""
    print("=" * 60)
    print("Manual Data Reset for Student Siddhat")
    print("=" * 60)
    
    # PostgreSQL reset
    print("\nStep 1: Resetting PostgreSQL data...")
    pg_success = reset_siddhat_postgresql()
    
    # JSON reset
    print("\nStep 2: Resetting user_progress.json...")
    json_success = reset_siddhat_json()
    
    # Summary
    print("\n" + "=" * 60)
    if pg_success and json_success:
        print("[SUCCESS] All resets completed successfully!")
    else:
        print("[WARNING] Some resets may have failed. Check the output above.")
    print("=" * 60)

if __name__ == "__main__":
    main()

