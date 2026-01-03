"""
Script to reassign 'Kitchen Safety' entries from 'Academic' to 'Food/Tech' category.
[cite: 2025-12-21]
"""
import json
from pathlib import Path
from datetime import datetime

def fix_kitchen_safety_category():
    """Reassign all 'Kitchen Safety' entries to Food/Tech category."""
    progress_file = Path(__file__).parent.parent / "assets" / "user_progress.json"
    
    if not progress_file.exists():
        print(f"Error: {progress_file} not found")
        return
    
    # Load data
    with open(progress_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    fixed_count = 0
    
    # Fix lesson_history entries
    for entry in data.get("lesson_history", []):
        lesson_name = entry.get("lesson", "")
        if "Kitchen Safety" in lesson_name or "kitchen_safety" in lesson_name.lower():
            # Update category in entry (add if missing)
            if entry.get("category") != "Food/Tech":
                entry["category"] = "Food/Tech"
                fixed_count += 1
            
            # Update category in scores if present (add if missing)
            scores = entry.get("scores", {})
            if scores.get("category") != "Food/Tech":
                scores["category"] = "Food/Tech"
                fixed_count += 1
    
    # Fix session entries
    for session_id, session_data in data.get("sessions", {}).items():
        for question in session_data.get("questions", []):
            lesson_name = question.get("lesson", "")
            if "Kitchen Safety" in lesson_name or "kitchen_safety" in lesson_name.lower():
                scores = question.get("scores", {})
                if scores.get("category") != "Food/Tech":
                    scores["category"] = "Food/Tech"
                    fixed_count += 1
    
    # Save updated data
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Fixed {fixed_count} Kitchen Safety entries - reassigned to Food/Tech category")
    print(f"Updated: {progress_file}")

if __name__ == "__main__":
    fix_kitchen_safety_category()

