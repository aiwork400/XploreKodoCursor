"""
Seed Academic and Food/Tech Track Syllabus with 20 Socratic Scenarios Each

Populates the Syllabus table with:
- Academic track: 20 scenarios (N3/N2 level)
- Food/Tech track: 20 scenarios (N5/N4 level)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Fix Unicode encoding for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from database.db_manager import SessionLocal, init_db
from models.curriculum import Syllabus


# 20 Academic Track Scenarios (N3/N2 Level)
ACADEMIC_SCENARIOS = [
    {
        "session": 1,
        "topic": "professor_meeting",
        "title": "Professor Meeting",
        "description": "Requesting an extension on a paper using Kenjougo (Humble).",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Academic Communication"
    },
    {
        "session": 2,
        "topic": "research_topic",
        "title": "Research Topic",
        "description": "Explaining 'Why this major?' in a university interview.",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N3",
        "duration_minutes": 15,
        "module_name": "Interview Skills"
    },
    {
        "session": 3,
        "topic": "library_protocol",
        "title": "Library Protocol",
        "description": "Asking about archives and citing sources using academic terms.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Research Skills"
    },
    {
        "session": 4,
        "topic": "seminar_debate",
        "title": "Seminar Debate",
        "description": "Disagreeing with a classmate politely using 'To omoimasu ga...'.",
        "skill_focus": "Logic / Empathy",
        "jlpt_level": "N3",
        "duration_minutes": 15,
        "module_name": "Academic Discussion"
    },
    {
        "session": 5,
        "topic": "campus_admin",
        "title": "Campus Administration",
        "description": "Applying for a scholarship and explaining financial need.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Administrative Communication"
    },
    {
        "session": 6,
        "topic": "thesis_proposal",
        "title": "Thesis Proposal",
        "description": "Presenting research methodology and objectives to a committee.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N2",
        "duration_minutes": 18,
        "module_name": "Research Skills"
    },
    {
        "session": 7,
        "topic": "group_project",
        "title": "Group Project Coordination",
        "description": "Assigning tasks and setting deadlines using formal language.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Collaboration"
    },
    {
        "session": 8,
        "topic": "office_hours",
        "title": "Office Hours Consultation",
        "description": "Asking for clarification on assignment requirements.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N3",
        "duration_minutes": 10,
        "module_name": "Academic Communication"
    },
    {
        "session": 9,
        "topic": "presentation_qna",
        "title": "Presentation Q&A",
        "description": "Responding to questions about your research findings.",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N2",
        "duration_minutes": 15,
        "module_name": "Academic Discussion"
    },
    {
        "session": 10,
        "topic": "email_professor",
        "title": "Email to Professor",
        "description": "Writing a formal email requesting a recommendation letter.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Written Communication"
    },
    {
        "session": 11,
        "topic": "lab_safety",
        "title": "Laboratory Safety Protocol",
        "description": "Explaining safety procedures and equipment usage.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Research Skills"
    },
    {
        "session": 12,
        "topic": "academic_disagreement",
        "title": "Academic Disagreement",
        "description": "Expressing different viewpoints in academic discourse.",
        "skill_focus": "Logic / Empathy",
        "jlpt_level": "N2",
        "duration_minutes": 15,
        "module_name": "Academic Discussion"
    },
    {
        "session": 13,
        "topic": "course_registration",
        "title": "Course Registration",
        "description": "Discussing course prerequisites and scheduling conflicts.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N3",
        "duration_minutes": 10,
        "module_name": "Administrative Communication"
    },
    {
        "session": 14,
        "topic": "research_ethics",
        "title": "Research Ethics Discussion",
        "description": "Explaining ethical considerations in academic research.",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N2",
        "duration_minutes": 15,
        "module_name": "Research Skills"
    },
    {
        "session": 15,
        "topic": "study_group",
        "title": "Study Group Organization",
        "description": "Coordinating study sessions and sharing notes.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Collaboration"
    },
    {
        "session": 16,
        "topic": "academic_apology",
        "title": "Academic Apology",
        "description": "Apologizing for missing a deadline and requesting accommodation.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N3",
        "duration_minutes": 10,
        "module_name": "Academic Communication"
    },
    {
        "session": 17,
        "topic": "data_analysis",
        "title": "Data Analysis Explanation",
        "description": "Explaining statistical methods and results to peers.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N2",
        "duration_minutes": 15,
        "module_name": "Research Skills"
    },
    {
        "session": 18,
        "topic": "peer_review",
        "title": "Peer Review Feedback",
        "description": "Providing constructive criticism on a classmate's work.",
        "skill_focus": "Logic / Empathy",
        "jlpt_level": "N2",
        "duration_minutes": 15,
        "module_name": "Academic Discussion"
    },
    {
        "session": 19,
        "topic": "graduation_requirements",
        "title": "Graduation Requirements",
        "description": "Clarifying degree requirements and credit hours.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N3",
        "duration_minutes": 12,
        "module_name": "Administrative Communication"
    },
    {
        "session": 20,
        "topic": "academic_networking",
        "title": "Academic Networking",
        "description": "Introducing yourself at a conference and discussing research interests.",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N2",
        "duration_minutes": 15,
        "module_name": "Professional Development"
    },
    {
        "session": 21,
        "topic": "why_japan_paradox",
        "title": "The 'Why Japan?' Paradox",
        "description": "Initial: 'Why did you choose a Japanese university over one in your home country or the West?' | Follow-up: 'If your research could be done more efficiently in English, what is the specific academic value of performing it in a Japanese-speaking environment?'",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N3",
        "duration_minutes": 18,
        "module_name": "High-Stakes Interview",
        "initial_question": "Why did you choose a Japanese university over one in your home country or the West?",
        "probing_question": "If your research could be done more efficiently in English, what is the specific academic value of performing it in a Japanese-speaking environment?"
    },
    {
        "session": 22,
        "topic": "research_contribution",
        "title": "The Research Contribution",
        "description": "Initial: 'How will your specific field of study benefit both Japan and your home country?' | Follow-up: 'Can you describe a specific social or economic problem in your country that your research directly addresses?'",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N3",
        "duration_minutes": 18,
        "module_name": "High-Stakes Interview",
        "initial_question": "How will your specific field of study benefit both Japan and your home country?",
        "probing_question": "Can you describe a specific social or economic problem in your country that your research directly addresses?"
    },
    {
        "session": 23,
        "topic": "language_barrier_challenge",
        "title": "The Language Barrier Challenge",
        "description": "Initial: 'What will you do if your primary research materials are only available in advanced technical Japanese (N1 level)?' | Follow-up: 'How do you plan to ensure the accuracy of your translations so your research remains academically sound?'",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N3",
        "duration_minutes": 18,
        "module_name": "High-Stakes Interview",
        "initial_question": "What will you do if your primary research materials are only available in advanced technical Japanese (N1 level)?",
        "probing_question": "How do you plan to ensure the accuracy of your translations so your research remains academically sound?"
    },
    {
        "session": 24,
        "topic": "professor_conflict",
        "title": "The Professor Conflict",
        "description": "Initial: 'If your laboratory professor suggests changing your research theme entirely, how would you respond?' | Follow-up: 'How would you balance your personal academic passion with the structural needs of the university lab?'",
        "skill_focus": "Logic / Empathy",
        "jlpt_level": "N3",
        "duration_minutes": 18,
        "module_name": "High-Stakes Interview",
        "initial_question": "If your laboratory professor suggests changing your research theme entirely, how would you respond?",
        "probing_question": "How would you balance your personal academic passion with the structural needs of the university lab?"
    },
    {
        "session": 25,
        "topic": "post_graduation_vision",
        "title": "Post-Graduation Vision",
        "description": "Initial: 'What is your 10-year goal after graduating from ExploraKodo and your chosen university?' | Follow-up: 'How does the Japanese concept of \"Shakai Kouken\" (Social Contribution) fit into that 10-year career plan?'",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N3",
        "duration_minutes": 18,
        "module_name": "High-Stakes Interview",
        "initial_question": "What is your 10-year goal after graduating from ExploraKodo and your chosen university?",
        "probing_question": "How does the Japanese concept of \"Shakai Kouken\" (Social Contribution) fit into that 10-year career plan?"
    }
]


# 20 Food/Tech Track Scenarios (N5/N4 Level)
FOOD_TECH_SCENARIOS = [
    {
        "session": 1,
        "topic": "customer_greeting",
        "title": "Customer Greeting",
        "description": "Standard 'Irasshaimase' and seating a party of four.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N5",
        "duration_minutes": 10,
        "module_name": "Customer Service"
    },
    {
        "session": 2,
        "topic": "error_handling",
        "title": "Error Handling",
        "description": "Apologizing for a late dish and offering a replacement.",
        "skill_focus": "Empathy",
        "jlpt_level": "N5",
        "duration_minutes": 12,
        "module_name": "Customer Service"
    },
    {
        "session": 3,
        "topic": "ai_concept",
        "title": "AI Concept Explanation",
        "description": "Explaining a 'Neural Network' in simple Japanese to a peer.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N4",
        "duration_minutes": 15,
        "module_name": "Technical Communication"
    },
    {
        "session": 4,
        "topic": "cleanliness_5s",
        "title": "5S Protocol",
        "description": "Explaining the '5S' (Seiri, Seiton...) protocol in the kitchen.",
        "skill_focus": "Logic / Horenso",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Safety & Hygiene"
    },
    {
        "session": 5,
        "topic": "daily_report",
        "title": "Daily Report",
        "description": "Ending the shift and reporting stock shortages.",
        "skill_focus": "Accuracy",
        "jlpt_level": "N4",
        "duration_minutes": 10,
        "module_name": "Operations"
    },
    {
        "session": 6,
        "topic": "menu_explanation",
        "title": "Menu Explanation",
        "description": "Describing dish ingredients and preparation methods to customers.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N5",
        "duration_minutes": 12,
        "module_name": "Customer Service"
    },
    {
        "session": 7,
        "topic": "allergy_inquiry",
        "title": "Allergy Inquiry",
        "description": "Asking about food allergies and dietary restrictions.",
        "skill_focus": "Accuracy",
        "jlpt_level": "N5",
        "duration_minutes": 10,
        "module_name": "Customer Service"
    },
    {
        "session": 8,
        "topic": "kitchen_coordination",
        "title": "Kitchen Coordination",
        "description": "Communicating order status and timing with kitchen staff.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Operations"
    },
    {
        "session": 9,
        "topic": "payment_processing",
        "title": "Payment Processing",
        "description": "Handling payment and explaining the bill to customers.",
        "skill_focus": "Tone / Honorifics",
        "jlpt_level": "N5",
        "duration_minutes": 10,
        "module_name": "Customer Service"
    },
    {
        "session": 10,
        "topic": "tech_bug_report",
        "title": "Technical Bug Report",
        "description": "Reporting a software issue to the development team.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Technical Communication"
    },
    {
        "session": 11,
        "topic": "reservation_handling",
        "title": "Reservation Handling",
        "description": "Taking and confirming restaurant reservations over the phone.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N5",
        "duration_minutes": 10,
        "module_name": "Customer Service"
    },
    {
        "session": 12,
        "topic": "code_review",
        "title": "Code Review Discussion",
        "description": "Discussing code improvements with team members.",
        "skill_focus": "Logic / Horenso",
        "jlpt_level": "N4",
        "duration_minutes": 15,
        "module_name": "Technical Communication"
    },
    {
        "session": 13,
        "topic": "complaint_resolution",
        "title": "Complaint Resolution",
        "description": "Addressing customer complaints with empathy and professionalism.",
        "skill_focus": "Empathy",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Customer Service"
    },
    {
        "session": 14,
        "topic": "inventory_check",
        "title": "Inventory Check",
        "description": "Reporting inventory levels and ordering supplies.",
        "skill_focus": "Accuracy",
        "jlpt_level": "N4",
        "duration_minutes": 10,
        "module_name": "Operations"
    },
    {
        "session": 15,
        "topic": "team_meeting",
        "title": "Team Meeting",
        "description": "Participating in a team meeting and sharing updates.",
        "skill_focus": "Conciseness",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Operations"
    },
    {
        "session": 16,
        "topic": "equipment_maintenance",
        "title": "Equipment Maintenance",
        "description": "Reporting equipment issues and requesting maintenance.",
        "skill_focus": "Technical Vocab",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Operations"
    },
    {
        "session": 17,
        "topic": "shift_handover",
        "title": "Shift Handover",
        "description": "Communicating important information to the next shift.",
        "skill_focus": "Logic / Horenso",
        "jlpt_level": "N4",
        "duration_minutes": 10,
        "module_name": "Operations"
    },
    {
        "session": 18,
        "topic": "training_new_staff",
        "title": "Training New Staff",
        "description": "Explaining procedures and protocols to new employees.",
        "skill_focus": "Contextual Logic",
        "jlpt_level": "N4",
        "duration_minutes": 15,
        "module_name": "Training"
    },
    {
        "session": 19,
        "topic": "quality_control",
        "title": "Quality Control",
        "description": "Reporting quality issues and discussing improvements.",
        "skill_focus": "Accuracy",
        "jlpt_level": "N4",
        "duration_minutes": 12,
        "module_name": "Operations"
    },
    {
        "session": 20,
        "topic": "customer_feedback",
        "title": "Customer Feedback",
        "description": "Collecting and responding to customer feedback.",
        "skill_focus": "Empathy",
        "jlpt_level": "N5",
        "duration_minutes": 12,
        "module_name": "Customer Service"
    }
]


def seed_syllabus(force: bool = False):
    """
    Seed the Syllabus table with Academic and Food/Tech track scenarios.
    
    Args:
        force: If True, automatically delete existing data and re-seed without prompting
    """
    # Initialize database
    init_db()
    
    db = SessionLocal()
    try:
        # Check for existing data
        existing_academic = db.query(Syllabus).filter(Syllabus.track == "Academic").first()
        existing_foodtech = db.query(Syllabus).filter(Syllabus.track == "Food/Tech").first()
        
        if existing_academic or existing_foodtech:
            if force:
                print("⚠️  Academic or Food/Tech syllabus data already exists. Force mode: deleting existing data...")
                db.query(Syllabus).filter(Syllabus.track == "Academic").delete()
                db.query(Syllabus).filter(Syllabus.track == "Food/Tech").delete()
                db.commit()
                print("✅ Deleted existing Academic and Food/Tech syllabus data.")
            else:
                print("⚠️  Academic or Food/Tech syllabus data already exists.")
                try:
                    response = input("Do you want to delete existing data and re-seed? (yes/no): ")
                    if response.lower() == "yes":
                        db.query(Syllabus).filter(Syllabus.track == "Academic").delete()
                        db.query(Syllabus).filter(Syllabus.track == "Food/Tech").delete()
                        db.commit()
                        print("✅ Deleted existing Academic and Food/Tech syllabus data.")
                    else:
                        print("❌ Seeding cancelled.")
                        return
                except (EOFError, KeyboardInterrupt):
                    print("\n❌ Seeding cancelled.")
                    return
        
        # Skill focus to topic mapping
        skill_to_topic = {
            "Tone / Honorifics": "tone_honorifics",
            "Vocabulary": "vocabulary",
            "Contextual Logic": "contextual_logic",
            "Conciseness": "conciseness",
            "Empathy": "empathy",
            "Accuracy": "accuracy",
            "Public Relations": "public_relations",
            "Technical Vocab": "technical_vocab",
            "Logic / Horenso": "logic_horenso",
            "Logic / Empathy": "logic_empathy"
        }
        
        # Difficulty level mapping
        difficulty_map = {
            "N5": "Beginner",
            "N4": "Intermediate",
            "N3": "Intermediate",
            "N2": "Advanced"
        }
        
        # Track directory mapping
        track_dirs = {
            "Academic": "academic",
            "Food/Tech": "tech"
        }
        
        total_added = 0
        
        # Seed Academic track
        print(f"📚 Seeding {len(ACADEMIC_SCENARIOS)} Academic scenarios...")
        for scenario in ACADEMIC_SCENARIOS:
            video_filename = f"session_{scenario['session']:02d}_{scenario['topic']}.mp4"
            video_path = f"assets/videos/{track_dirs['Academic']}/{video_filename}"
            topic = skill_to_topic.get(scenario['skill_focus'], scenario['topic'])
            difficulty_level = difficulty_map.get(scenario['jlpt_level'], "Intermediate")
            
            lesson = Syllabus(
                track="Academic",
                lesson_title=f"Session #{scenario['session']}: {scenario['title']}",
                lesson_description=scenario['description'],
                lesson_number=scenario['session'],
                video_path=video_path,
                video_filename=video_filename,
                language="ja",
                topic=topic,
                duration_minutes=scenario['duration_minutes'],
                difficulty_level=difficulty_level,
                module_name=scenario['module_name'],
                sequence_order=scenario['session']
            )
            
            db.add(lesson)
            print(f"  ✓ Added Academic Session #{scenario['session']}: {scenario['title']} ({scenario['jlpt_level']})")
            total_added += 1
        
        # Seed Food/Tech track
        print(f"\n🍜 Seeding {len(FOOD_TECH_SCENARIOS)} Food/Tech scenarios...")
        for scenario in FOOD_TECH_SCENARIOS:
            video_filename = f"session_{scenario['session']:02d}_{scenario['topic']}.mp4"
            video_path = f"assets/videos/{track_dirs['Food/Tech']}/{video_filename}"
            topic = skill_to_topic.get(scenario['skill_focus'], scenario['topic'])
            difficulty_level = difficulty_map.get(scenario['jlpt_level'], "Intermediate")
            
            lesson = Syllabus(
                track="Food/Tech",
                lesson_title=f"Session #{scenario['session']}: {scenario['title']}",
                lesson_description=scenario['description'],
                lesson_number=scenario['session'],
                video_path=video_path,
                video_filename=video_filename,
                language="ja",
                topic=topic,
                duration_minutes=scenario['duration_minutes'],
                difficulty_level=difficulty_level,
                module_name=scenario['module_name'],
                sequence_order=scenario['session']
            )
            
            db.add(lesson)
            print(f"  ✓ Added Food/Tech Session #{scenario['session']}: {scenario['title']} ({scenario['jlpt_level']})")
            total_added += 1
        
        db.commit()
        
        # Summary
        print(f"\n✅ Successfully seeded {total_added} scenarios!")
        print(f"📊 Summary:")
        print(f"   Academic Track:")
        print(f"     - N3 Level: {sum(1 for s in ACADEMIC_SCENARIOS if s['jlpt_level'] == 'N3')} sessions")
        print(f"     - N2 Level: {sum(1 for s in ACADEMIC_SCENARIOS if s['jlpt_level'] == 'N2')} sessions")
        print(f"     - Modules: {len(set(s['module_name'] for s in ACADEMIC_SCENARIOS))} different modules")
        print(f"   Food/Tech Track:")
        print(f"     - N5 Level: {sum(1 for s in FOOD_TECH_SCENARIOS if s['jlpt_level'] == 'N5')} sessions")
        print(f"     - N4 Level: {sum(1 for s in FOOD_TECH_SCENARIOS if s['jlpt_level'] == 'N4')} sessions")
        print(f"     - Modules: {len(set(s['module_name'] for s in FOOD_TECH_SCENARIOS))} different modules")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding syllabus: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    # Check for --force flag
    force = "--force" in sys.argv or "-f" in sys.argv
    seed_syllabus(force=force)

