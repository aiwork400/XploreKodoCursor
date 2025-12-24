# Triple-Track Syllabus - Complete Overview

## Summary

All three tracks have been fully populated with 20 Socratic scenarios each:

- **Care-giving**: 20 sessions (N4-N3 level)
- **Academic**: 20 sessions (N3-N2 level)
- **Food/Tech**: 20 sessions (N5-N4 level)

**Total: 60 sessions across all tracks**

## Track Breakdown

### Care-giving Track (N4-N3)

**Focus**: Kaigo (Caregiving) training for healthcare workers

**JLPT Distribution**:
- N4 Level: 10 sessions (Sessions 1-10)
- N3 Level: 10 sessions (Sessions 11-20)

**Key Modules**:
- Daily Care Basics
- Meal Service
- Physical Assistance
- Medical Communication
- Personal Care
- Communication Skills
- Emergency Response
- Specialized Care
- Safety Protocols
- Professional Communication

**Skill Focus Distribution**:
- Tone / Honorifics: 4 sessions
- Vocabulary: 1 session
- Contextual Logic: 3 sessions
- Conciseness: 2 sessions
- Empathy: 2 sessions
- Accuracy: 2 sessions
- Public Relations: 2 sessions
- Technical Vocab: 3 sessions
- Logic / Horenso: 1 session

### Academic Track (N3-N2)

**Focus**: Ryugaku (Study Abroad) preparation for university students

**JLPT Distribution**:
- N3 Level: 13 sessions
- N2 Level: 7 sessions

**Key Modules**:
- Academic Communication
- Interview Skills
- Research Skills
- Academic Discussion
- Administrative Communication
- Collaboration
- Written Communication
- Professional Development

**Sample Sessions**:
1. Professor Meeting - Requesting extension using Kenjougo
2. Research Topic - Explaining "Why this major?" in interview
3. Library Protocol - Asking about archives and citations
4. Seminar Debate - Disagreeing politely with "To omoimasu ga..."
5. Campus Admin - Applying for scholarship

**Skill Focus Distribution**:
- Tone / Honorifics: 4 sessions
- Contextual Logic: 4 sessions
- Technical Vocab: 4 sessions
- Logic / Empathy: 3 sessions
- Conciseness: 5 sessions

### Food/Tech Track (N5-N4)

**Focus**: Industrial workplace communication for food service and technology sectors

**JLPT Distribution**:
- N5 Level: 7 sessions
- N4 Level: 13 sessions

**Key Modules**:
- Customer Service
- Technical Communication
- Safety & Hygiene
- Operations
- Training

**Sample Sessions**:
1. Customer Greeting - "Irasshaimase" and seating
2. Error Handling - Apologizing for late dish
3. AI Concept - Explaining "Neural Network" simply
4. Cleanliness - 5S protocol (Seiri, Seiton...)
5. Daily Report - Reporting stock shortages

**Skill Focus Distribution**:
- Tone / Honorifics: 2 sessions
- Empathy: 3 sessions
- Technical Vocab: 4 sessions
- Logic / Horenso: 3 sessions
- Accuracy: 4 sessions
- Conciseness: 3 sessions
- Contextual Logic: 1 session

## Mastery Heatmap Data Coverage

All tracks now have comprehensive data for the Progress Dashboard heatmap:

### Skill Categories Tracked:
1. **Vocabulary** - Technical and domain-specific terminology
2. **Tone/Honorifics** - Appropriate use of Keigo, Sonkeigo, Kenjougo
3. **Contextual Logic** - Understanding and applying context-appropriate language

### Track Coverage:
- ✅ **Care-giving**: 20 sessions covering all skill categories
- ✅ **Academic**: 20 sessions covering all skill categories
- ✅ **Food/Tech**: 20 sessions covering all skill categories

### Assessment Integration:
Each session includes:
- **Topic**: Mapped from skill focus for Socratic Assessment
- **Track**: Properly set for mastery score calculation
- **Language**: Japanese (ja) for all sessions
- **Difficulty**: Mapped from JLPT level

## Database Structure

### Syllabus Table Fields:
- `track`: "Care-giving", "Academic", or "Food/Tech"
- `lesson_title`: "Session #X: [Title]"
- `lesson_description`: Socratic challenge description
- `lesson_number`: 1-20 (per track)
- `video_path`: `assets/videos/{track_dir}/session_XX_topic.mp4`
- `language`: "ja" (Japanese)
- `topic`: Skill focus topic (e.g., "tone_honorifics", "vocabulary")
- `difficulty_level`: "Beginner" (N5), "Intermediate" (N4/N3), "Advanced" (N2)
- `module_name`: Module/category name
- `sequence_order`: Session number

## Seeding Scripts

### Individual Track Seeding:
```bash
# Care-giving track
python scripts/seed_caregiving_syllabus.py

# Academic and Food/Tech tracks
python scripts/seed_academic_foodtech_syllabus.py
```

### Verification:
```python
from database.db_manager import SessionLocal
from models.curriculum import Syllabus

db = SessionLocal()
caregiving = db.query(Syllabus).filter(Syllabus.track == "Care-giving").count()
academic = db.query(Syllabus).filter(Syllabus.track == "Academic").count()
foodtech = db.query(Syllabus).filter(Syllabus.track == "Food/Tech").count()
print(f"Care-giving: {caregiving}, Academic: {academic}, Food/Tech: {foodtech}")
db.close()
```

## Progress Dashboard Integration

The Mastery Heatmap now has full data coverage:

### Vertical Axis (Tracks):
- Care-giving
- Academic
- Food/Tech

### Horizontal Axis (Skills):
- Vocabulary
- Tone/Honorifics
- Contextual Logic

### Data Flow:
1. Student completes Video Hub assessment
2. Evaluation saved with `track` and `affected_skills`
3. `calculate_mastery_scores()` aggregates by track and skill
4. Heatmap displays comprehensive performance data

## Video File Structure

### Directory Layout:
```
assets/videos/
├── kaigo/          # Care-giving videos
│   ├── session_01_morning_greeting.mp4
│   ├── session_02_meal_assistance.mp4
│   └── ...
├── academic/        # Academic videos
│   ├── session_01_professor_meeting.mp4
│   ├── session_02_research_topic.mp4
│   └── ...
└── tech/           # Food/Tech videos
    ├── session_01_customer_greeting.mp4
    ├── session_02_error_handling.mp4
    └── ...
```

## Usage

### Accessing Sessions:
1. Navigate to **Video Hub** in dashboard
2. Select track (Care-giving, Academic, or Food/Tech)
3. Choose language (Japanese)
4. Select session from dropdown
5. Click "Practice Now" to start Socratic Assessment

### Progress Tracking:
1. Navigate to **Progress** tab
2. View heatmap showing performance across all tracks
3. See AI-generated feedback on weak points
4. Get recommendations for improvement

## Future Enhancements

1. **Multi-language Support**: Add English and Nepali versions
2. **Video Integration**: Link actual video files
3. **Progress Analytics**: Track completion rates per track
4. **Adaptive Learning**: Suggest sessions based on weak points
5. **Prerequisites**: Define learning paths between sessions

