"""
Seed Care-giving Track Syllabus with 20 Socratic Scenarios

Populates the Syllabus table with Care-giving track lessons covering N4 to N3 level Japanese.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from database.db_manager import SessionLocal, init_db
from models.curriculum import Syllabus


# 20 Socratic Scenarios for Care-giving Track
CARE_GIVING_SCENARIOS = [
    {
        "session": 1,
        "topic": "morning_greeting",
        "title": "Morning Greeting",
        "description": "Use Keigo to wake a resident and check their mood.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N4",
        "duration_minutes": 10,
        "module_name": "Daily Care Basics"
    },
    {
        "session": 2,
        "topic": "meal_assistance",
        "title": "Meal Assistance",
        "description": "Explaining the menu while using Sonkeigo (Respectful).",
        "skill_focus": "Vocabulary",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Meal Service"
    },
    {
        "session": 3,
        "topic": "mobility_help",
        "title": "Mobility Help",
        "description": "Guiding a resident to a wheelchair using 'O-negai shimasu.'",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N4",
        "duration_minutes": 15,
        "module_name": "Physical Assistance"
    },
    {
        "session": 4,
        "topic": "vital_signs",
        "title": "Vital Signs",
        "description": "Reporting a temperature of 38.5°C to the Head Nurse (Horenso).",
        "skill_focus": "Conciseness",
        "jlpt_level": "N4",
        "duration_minutes": 10,
        "module_name": "Medical Communication"
    },
    {
        "session": 5,
        "topic": "bathing_prep",
        "title": "Bathing Preparation",
        "description": "Explaining the water temperature politely using 'Atsui/Nurui.'",
        "skill_focus": "Empathy",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Personal Care"
    },
    {
        "session": 6,
        "topic": "medication",
        "title": "Medication Administration",
        "description": "Confirming identity and medication type with high precision.",
        "skill_focus": "Accuracy",
        "jlpt_level": "N4",
        "duration_minutes": 15,
        "module_name": "Medical Communication"
    },
    {
        "session": 7,
        "topic": "family_visit",
        "title": "Family Visit",
        "description": "Greeting a resident's family and explaining today's activities.",
        "skill_focus": "Public Relations",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Communication Skills"
    },
    {
        "session": 8,
        "topic": "night_shift",
        "title": "Night Shift Response",
        "description": "Responding to a call-button at 2 AM with a calm, gentle tone.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N4",
        "duration_minutes": 10,
        "module_name": "Emergency Response"
    },
    {
        "session": 9,
        "topic": "dietary_needs",
        "title": "Dietary Needs",
        "description": "Explaining why a resident cannot have certain allergens.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Meal Service"
    },
    {
        "session": 10,
        "topic": "emergency_fall",
        "title": "Emergency: Fall Incident",
        "description": "Describing a fall incident using the 'Who/When/Where' logic.",
        "skill_focus": "Logic / Horenso",
        "jlpt_level": "N4",
        "duration_minutes": 15,
        "module_name": "Emergency Response"
    },
    {
        "session": 11,
        "topic": "pain_assessment",
        "title": "Pain Assessment",
        "description": "Asking about pain level using appropriate Keigo and empathy.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Medical Communication"
    },
    {
        "session": 12,
        "topic": "dementia_care",
        "title": "Dementia Care Communication",
        "description": "Communicating with residents with dementia using simple, respectful language.",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N3",
        "duration_minutes": 15,
        "module_name": "Specialized Care"
    },
    {
        "session": 13,
        "topic": "transfer_technique",
        "title": "Transfer Technique Explanation",
        "description": "Explaining safe transfer techniques using technical vocabulary.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Physical Assistance"
    },
    {
        "session": 14,
        "topic": "care_plan_discussion",
        "title": "Care Plan Discussion",
        "description": "Discussing care plan changes with family using formal language.",
        "skill_focus": "Public Relations",
        "jlpt_level": "N3",
        "duration_minutes": 15,
        "module_name": "Communication Skills"
    },
    {
        "session": 15,
        "topic": "infection_control",
        "title": "Infection Control Protocol",
        "description": "Explaining handwashing and infection control procedures.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N3",
        "duration_minutes": 10,
        "module_name": "Safety Protocols"
    },
    {
        "session": 16,
        "topic": "emotional_support",
        "title": "Emotional Support",
        "description": "Providing emotional support to a distressed resident using empathetic language.",
        "skill_focus": "Empathy",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Communication Skills"
    },
    {
        "session": 17,
        "topic": "medication_side_effects",
        "title": "Medication Side Effects",
        "description": "Explaining potential side effects and monitoring requirements.",
        "skill_focus": "Accuracy",
        "jlpt_level": "N3",
        "duration_minutes": 15,
        "module_name": "Medical Communication"
    },
    {
        "session": 18,
        "topic": "end_of_life_care",
        "title": "End of Life Care Communication",
        "description": "Communicating with dignity and respect in sensitive situations.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N3",
        "duration_minutes": 15,
        "module_name": "Specialized Care"
    },
    {
        "session": 19,
        "topic": "team_handover",
        "title": "Team Handover Report",
        "description": "Providing concise shift handover using Horenso format.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Professional Communication"
    },
    {
        "session": 20,
        "topic": "cultural_sensitivity",
        "title": "Cultural Sensitivity",
        "description": "Understanding and respecting cultural differences in caregiving.",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N3",
        "duration_minutes": 15,
        "module_name": "Communication Skills"
    }
]


def seed_syllabus():
    """Seed the Syllabus table with Care-giving track scenarios."""
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        # Check if data already exists
        existing = db.query(Syllabus).filter(Syllabus.track == "Care-giving").first()
        if existing:
            print("⚠️  Care-giving syllabus data already exists. Skipping seed.")
            response = input("Do you want to delete existing data and re-seed? (yes/no): ")
            if response.lower() == "yes":
                db.query(Syllabus).filter(Syllabus.track == "Care-giving").delete()
                db.commit()
                print("✅ Deleted existing Care-giving syllabus data.")
            else:
                print("❌ Seeding cancelled.")
                return
        
        print(f"📚 Seeding {len(CARE_GIVING_SCENARIOS)} Care-giving scenarios...")
        
        for scenario in CARE_GIVING_SCENARIOS:
            # Create video path (placeholder - videos should be added later)
            video_filename = f"session_{scenario['session']:02d}_{scenario['topic']}.mp4"
            video_path = f"assets/videos/kaigo/{video_filename}"
            
            # Map skill focus to topic for Socratic Assessment
            skill_to_topic = {
                "Tone / Honorifics": "tone_honorifics",
                "Vocabulary": "vocabulary",
                "Contextual Logic": "contextual_logic",
                "Conciseness": "conciseness",
                "Empathy": "empathy",
                "Accuracy": "accuracy",
                "Public Relations": "public_relations",
                "Technical Vocab": "technical_vocab",
                "Logic / Horenso": "logic_horenso"
            }
            
            topic = skill_to_topic.get(scenario['skill_focus'], scenario['topic'])
            
            # Determine difficulty level based on JLPT
            difficulty_map = {
                "N4": "Intermediate",
                "N3": "Advanced"
            }
            difficulty_level = difficulty_map.get(scenario['jlpt_level'], "Intermediate")
            
            lesson = Syllabus(
                track="Care-giving",
                lesson_title=f"Session #{scenario['session']}: {scenario['title']}",
                lesson_description=scenario['description'],
                lesson_number=scenario['session'],
                video_path=video_path,
                video_filename=video_filename,
                language="ja",  # Japanese language for Care-giving track
                topic=topic,
                duration_minutes=scenario['duration_minutes'],
                difficulty_level=difficulty_level,
                module_name=scenario['module_name'],
                sequence_order=scenario['session']
            )
            
            db.add(lesson)
            print(f"  ✓ Added Session #{scenario['session']}: {scenario['title']} ({scenario['jlpt_level']})")
        
        db.commit()
        print(f"\n✅ Successfully seeded {len(CARE_GIVING_SCENARIOS)} Care-giving scenarios!")
        print(f"📊 Summary:")
        print(f"   - N4 Level: {sum(1 for s in CARE_GIVING_SCENARIOS if s['jlpt_level'] == 'N4')} sessions")
        print(f"   - N3 Level: {sum(1 for s in CARE_GIVING_SCENARIOS if s['jlpt_level'] == 'N3')} sessions")
        print(f"   - Modules: {len(set(s['module_name'] for s in CARE_GIVING_SCENARIOS))} different modules")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding syllabus: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_syllabus()

