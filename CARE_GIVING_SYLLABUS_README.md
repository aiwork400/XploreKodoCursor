# Care-giving Track Syllabus - 20 Socratic Scenarios

## Overview

The Care-giving track syllabus has been populated with 20 Socratic scenarios covering N4 to N3 level Japanese, designed to prepare candidates for real-world caregiving situations in Japan.

## Session Breakdown

### N4 Level Sessions (1-10)

| Session | Topic | Socratic Challenge | Skill Focus | Module |
|---------|-------|-------------------|-------------|--------|
| 1 | Morning Greeting | Use Keigo to wake a resident and check their mood | Tone / Honorifics | Daily Care Basics |
| 2 | Meal Assistance | Explaining the menu while using Sonkeigo (Respectful) | Vocabulary | Meal Service |
| 3 | Mobility Help | Guiding a resident to a wheelchair using "O-negai shimasu." | Contextual Logic | Physical Assistance |
| 4 | Vital Signs | Reporting a temperature of 38.5°C to the Head Nurse (Horenso) | Conciseness | Medical Communication |
| 5 | Bathing Preparation | Explaining the water temperature politely using "Atsui/Nurui." | Empathy | Personal Care |
| 6 | Medication Administration | Confirming identity and medication type with high precision | Accuracy | Medical Communication |
| 7 | Family Visit | Greeting a resident's family and explaining today's activities | Public Relations | Communication Skills |
| 8 | Night Shift Response | Responding to a call-button at 2 AM with a calm, gentle tone | Tone / Honorifics | Emergency Response |
| 9 | Dietary Needs | Explaining why a resident cannot have certain allergens | Technical Vocab | Meal Service |
| 10 | Emergency: Fall Incident | Describing a fall incident using the "Who/When/Where" logic | Logic / Horenso | Emergency Response |

### N3 Level Sessions (11-20)

| Session | Topic | Socratic Challenge | Skill Focus | Module |
|---------|-------|-------------------|-------------|--------|
| 11 | Pain Assessment | Asking about pain level using appropriate Keigo and empathy | Tone / Honorifics | Medical Communication |
| 12 | Dementia Care Communication | Communicating with residents with dementia using simple, respectful language | Contextual Logic | Specialized Care |
| 13 | Transfer Technique Explanation | Explaining safe transfer techniques using technical vocabulary | Technical Vocab | Physical Assistance |
| 14 | Care Plan Discussion | Discussing care plan changes with family using formal language | Public Relations | Communication Skills |
| 15 | Infection Control Protocol | Explaining handwashing and infection control procedures | Technical Vocab | Safety Protocols |
| 16 | Emotional Support | Providing emotional support to a distressed resident using empathetic language | Empathy | Communication Skills |
| 17 | Medication Side Effects | Explaining potential side effects and monitoring requirements | Accuracy | Medical Communication |
| 18 | End of Life Care Communication | Communicating with dignity and respect in sensitive situations | Tone / Honorifics | Specialized Care |
| 19 | Team Handover Report | Providing concise shift handover using Horenso format | Conciseness | Professional Communication |
| 20 | Cultural Sensitivity | Understanding and respecting cultural differences in caregiving | Contextual Logic | Communication Skills |

## Skill Focus Distribution

- **Tone / Honorifics**: 4 sessions (Sessions 1, 8, 11, 18)
- **Vocabulary**: 1 session (Session 2)
- **Contextual Logic**: 3 sessions (Sessions 3, 12, 20)
- **Conciseness**: 2 sessions (Sessions 4, 19)
- **Empathy**: 2 sessions (Sessions 5, 16)
- **Accuracy**: 2 sessions (Sessions 6, 17)
- **Public Relations**: 2 sessions (Sessions 7, 14)
- **Technical Vocab**: 3 sessions (Sessions 9, 13, 15)
- **Logic / Horenso**: 1 session (Session 10)

## Module Distribution

1. **Daily Care Basics**: 1 session
2. **Meal Service**: 2 sessions
3. **Physical Assistance**: 2 sessions
4. **Medical Communication**: 4 sessions
5. **Personal Care**: 1 session
6. **Communication Skills**: 4 sessions
7. **Emergency Response**: 2 sessions
8. **Specialized Care**: 2 sessions
9. **Safety Protocols**: 1 session
10. **Professional Communication**: 1 session

## Database Structure

Each session is stored in the `syllabus` table with:

- **track**: "Care-giving"
- **language**: "ja" (Japanese)
- **topic**: Mapped from skill focus (e.g., "tone_honorifics", "vocabulary")
- **difficulty_level**: "Intermediate" (N4) or "Advanced" (N3)
- **video_path**: `assets/videos/kaigo/session_XX_topic.mp4`
- **sequence_order**: Session number (1-20)

## Usage

### Accessing Sessions

1. Navigate to **Video Hub** in the dashboard
2. Select **Care-giving** track
3. Choose **Japanese** language
4. Select a session from the dropdown

### Socratic Assessment

Each session triggers a Socratic Assessment when "Practice Now" is clicked:
- Questions are tailored to the session's skill focus
- Evaluation uses track-specific criteria
- Results are tracked in the Progress Dashboard

### Progress Tracking

Performance is tracked by:
- **Track**: Care-giving
- **Skill Categories**: Vocabulary, Tone/Honorifics, Contextual Logic
- **Session Topic**: Used for targeted assessment

## Video Files

**Note**: Video files are placeholders. Actual video files should be:
- Placed in `assets/videos/kaigo/` directory
- Named according to pattern: `session_XX_topic.mp4`
- Format: MP4, WebM, or OGG

Example:
- `assets/videos/kaigo/session_01_morning_greeting.mp4`
- `assets/videos/kaigo/session_02_meal_assistance.mp4`

## Seeding Script

To re-seed or update the syllabus:

```bash
python scripts/seed_caregiving_syllabus.py
```

The script will:
- Check for existing data
- Prompt before deleting existing entries
- Insert all 20 sessions
- Provide a summary of inserted data

## Future Enhancements

1. **Multi-language Support**: Add English and Nepali versions
2. **Video Integration**: Link to actual video files
3. **Progress Tracking**: Track completion per session
4. **Adaptive Learning**: Adjust difficulty based on performance
5. **Session Prerequisites**: Define learning paths

