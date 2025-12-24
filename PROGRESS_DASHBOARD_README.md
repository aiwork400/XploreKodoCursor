# Student Performance Heatmap - Progress Dashboard

## Overview

The Progress Dashboard provides a comprehensive visualization of student performance across the Triple-Track Coaching system, with mastery scores calculated from Socratic Assessment results.

## Features

### 1. Data Aggregation

The `calculate_mastery_scores()` function:
- Queries `dialogue_history` from `curriculum_progress` table
- Extracts evaluation results from Video Hub assessments
- Calculates mastery scores (0-100%) for each track and skill category
- Tracks performance across:
  - **Tracks**: Care-giving, Academic, Food/Tech
  - **Skills**: Vocabulary, Tone/Honorifics, Contextual Logic

### 2. Score Calculation Logic

#### Score Assignment
- **Acceptable**: 100% (boosts all skills)
- **Partially Acceptable**: 50% (lowers affected skills)
- **Non-Acceptable**: 0% (lowers affected skills)

#### Skill Category Detection
The system identifies which skills were affected by:
1. **Primary Method**: Uses `affected_skills` field from evaluation (explicitly marked by AI)
2. **Fallback Method**: Keyword matching in feedback/explanation:
   - **Vocabulary**: "vocabulary", "terminology", "word", "term"
   - **Tone/Honorifics**: "tone", "honorific", "desu", "masu", "keigo", "polite", "formal"
   - **Contextual Logic**: "meaning", "context", "logic", "understand", "comprehension"

#### Database Sync
- Every evaluation result is saved in `dialogue_history` with:
  - `evaluation.status`: Acceptable/Partially Acceptable/Non-Acceptable
  - `evaluation.affected_skills`: List of affected skill categories
  - `session_snapshot.track`: Track context
  - `session_snapshot.topic`: Lesson topic

### 3. Visualization

#### Heatmap Chart
- **Vertical Axis**: Tracks (Care-giving, Academic, Food/Tech)
- **Horizontal Axis**: Skill Categories (Vocabulary, Tone/Honorifics, Contextual Logic)
- **Color Scale**: Red-Yellow-Green (0-100%)
- **Interactive**: Hover to see exact scores

#### Radar Chart
- Multi-track comparison
- Shows performance across all three tracks simultaneously
- Useful for identifying relative strengths/weaknesses

### 4. AI-Generated Weak Point Summary

The `generate_weak_point_summary()` function:
- Uses Gemini AI to analyze mastery scores
- Generates personalized feedback in Sensei's voice
- Highlights:
  - Areas of excellence
  - Weakest areas needing improvement
  - Specific recommendations (e.g., "Try Session #4 again")

**Example Output:**
> "Sensei says: You are excelling in Tech Logic (85%), but your Honorifics (Keigo) in the Care-giving track needs more practice (45%). Try reviewing Session #4 on Care-giving basics again."

### 5. Detailed Breakdown

- Progress bars for each track and skill
- Color-coded indicators:
  - 🟢 Green: 70%+ (Good)
  - 🟠 Orange: 50-69% (Needs Improvement)
  - 🔴 Red: <50% (Critical)

### 6. Recommendations

Automatically identifies:
- Top 3 weakest areas
- Specific track and skill combinations
- Actionable next steps

## Usage

### Accessing the Dashboard

1. Navigate to **Progress** tab in the dashboard
2. Select a candidate from the dropdown (or enter candidate ID)
3. View heatmap, radar chart, and AI summary
4. Review detailed breakdown and recommendations

### Data Flow

```
Video Hub Assessment
    ↓
VideoSocraticAssessmentTool evaluates response
    ↓
Evaluation saved to dialogue_history
    (includes: status, affected_skills, track)
    ↓
calculate_mastery_scores() aggregates data
    ↓
Progress Dashboard displays visualization
```

## Database Schema

### dialogue_history Entry Structure

```json
{
  "question_id": "video_1",
  "question": {...},
  "candidate_answer": "User's response",
  "answer_timestamp": "2025-12-24T10:00:00Z",
  "evaluation": {
    "status": "Partially Acceptable",
    "explanation": "...",
    "feedback": "...",
    "affected_skills": ["Tone/Honorifics"],
    "can_resume_video": false
  },
  "session_snapshot": {
    "track": "Care-giving",
    "topic": "omotenashi",
    "video_timestamp": 125.5,
    "session_start": "2025-12-24T10:00:00Z",
    "source": "video_hub"
  }
}
```

## Implementation Details

### Files Modified

1. **dashboard/app.py**
   - Added `calculate_mastery_scores()` function
   - Added `generate_weak_point_summary()` function
   - Added `show_progress_dashboard()` function
   - Added "Progress" to page navigation

2. **agency/training_agent/video_socratic_assessment_tool.py**
   - Enhanced evaluation to include `affected_skills` field
   - Updated AI prompt to explicitly identify affected skill categories
   - Added fallback logic for skill detection

### Dependencies

- **plotly**: For heatmap and radar chart visualizations
- **gemini-pro**: For AI-generated summaries (optional, has fallback)

## Future Enhancements

1. **Time-based Trends**: Track performance over time
2. **Session Recommendations**: Suggest specific video sessions based on weak points
3. **Goal Setting**: Allow students to set mastery goals
4. **Comparison**: Compare performance across multiple candidates
5. **Export**: Export performance data as PDF or CSV

## Notes

- Scores are calculated as averages of all assessment results for each track/skill combination
- If no assessments exist, all scores default to 0%
- The system gracefully handles missing data and evaluation errors
- AI summary generation has a fallback if Gemini is unavailable

