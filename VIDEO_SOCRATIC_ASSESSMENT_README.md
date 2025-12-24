# Video-Triggered Socratic Assessment Implementation

## Overview

This document describes the refined Socratic Assessment Logic for the Video Hub's 'Practice Now' feature, including session snapshot capture, evaluation rubric, and feedback loop.

## Components

### 1. VideoSocraticAssessmentTool (`agency/training_agent/video_socratic_assessment_tool.py`)

A specialized tool for video-triggered Socratic Assessment with:

#### Session Snapshot
When 'Practice Now' is clicked, the tool receives:
- **track**: Coaching track (`Care-giving`, `Academic`, or `Food/Tech`)
- **topic**: Lesson topic (e.g., `omotenashi`, `knowledge_base`)
- **video_timestamp**: Current video playback position in seconds

#### Evaluation Rubric

The tool implements a three-tier evaluation system:

1. **Acceptable** ✅
   - Correct vocabulary appropriate for the track context
   - Appropriate tone (Desu/Masu vs. Plain form based on track)
   - Grammar is correct
   - Meaning is clear and accurate
   - **Result**: User can continue or resume video

2. **Partially Acceptable** ⚠️
   - Grammar is correct
   - BUT tone is wrong (e.g., used Plain form when Desu/Masu was required, or vice versa)
   - OR vocabulary is slightly off but meaning is preserved
   - Meaning is still understandable
   - **Result**: Feedback required before video resumption

3. **Non-Acceptable** ❌
   - Meaning is lost or incorrect
   - Wrong terminology used
   - Grammar errors that affect comprehension
   - Response doesn't address the question
   - **Result**: Must try again with correct approach

#### Track-Specific Tone Requirements

- **Care-giving**: Polite, respectful language (Desu/Masu form). Gentle and caring tone.
- **Academic**: Formal academic language (Desu/Masu form). Professional and clear tone.
- **Food/Tech**: Professional workplace language. Can use Plain form in technical contexts, but Desu/Masu for customer-facing situations.

### 2. Feedback Loop

The feedback loop ensures users understand their mistakes before continuing:

1. **Evaluation**: Response is evaluated using Gemini AI with track-specific criteria
2. **Feedback Display**: Detailed explanation of why the response received its status
3. **Acknowledgment Required**: For "Partially Acceptable" or "Non-Acceptable" responses:
   - User must click "✅ I Understand the Feedback"
   - System explains what needs improvement
   - Video resumption is blocked until acknowledgment
4. **Continuation Options**: After acknowledgment:
   - **Try Again**: Re-attempt the same question
   - **Next Question**: Move to the next question
   - **Resume Video**: Return to video playback

### 3. Video Hub Integration (`dashboard/app.py`)

The Video Hub now includes:

#### Timestamp Capture
- JavaScript tracks video playback position
- Timestamp is captured when "Practice Now" is clicked
- Stored in session snapshot for assessment context

#### Assessment Flow
1. User clicks "Practice Now" → Session snapshot created
2. Question displayed → User enters response
3. Response evaluated → Status assigned (Acceptable/Partially Acceptable/Non-Acceptable)
4. Feedback shown → Acknowledgment required if not Acceptable
5. User can continue → Try again, next question, or resume video

## Usage Example

### Starting an Assessment

```python
from agency.training_agent.video_socratic_assessment_tool import VideoSocraticAssessmentTool

tool = VideoSocraticAssessmentTool(
    candidate_id="candidate_123",
    track="Care-giving",
    topic="omotenashi",
    video_timestamp=125.5,  # 2 minutes 5 seconds into video
    start_new_session=True
)

result = tool.run()  # Returns question
```

### Evaluating a Response

```python
tool = VideoSocraticAssessmentTool(
    candidate_id="candidate_123",
    track="Care-giving",
    topic="omotenashi",
    video_timestamp=125.5,
    candidate_response="患者さんに丁寧に挨拶します。",  # User's response
    start_new_session=False
)

result = tool.run()  # Returns evaluation with status and feedback
```

## Evaluation Prompt Structure

The tool uses Gemini AI with a structured prompt that includes:

1. **Question Context**: The original question asked
2. **Candidate Response**: User's submitted answer
3. **Track Context**: Specific tone and vocabulary requirements
4. **Rubric Definition**: Clear criteria for each status level
5. **JSON Response**: Structured evaluation with status, explanation, and feedback

## Database Integration

Assessment results are stored in `curriculum_progress.dialogue_history` with:

```json
{
  "question_id": "video_1",
  "question": {...},
  "candidate_answer": "User's response",
  "answer_timestamp": "2025-12-24T10:00:00Z",
  "evaluation": {
    "status": "Partially Acceptable",
    "explanation": "Grammar correct but tone wrong...",
    "feedback": "Use Desu/Masu form for caregiving context",
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

## Limitations and Future Enhancements

### Current Limitations

1. **Timestamp Capture**: Full JavaScript-to-Python timestamp communication requires a custom Streamlit component. Current implementation uses a workaround.

2. **Video Pause**: The video doesn't automatically pause when "Practice Now" is clicked. This would require additional JavaScript integration.

### Future Enhancements

1. **Custom Streamlit Component**: Create a component for seamless JavaScript-Python communication
2. **Auto-pause Video**: Automatically pause video when assessment starts
3. **Progress Tracking**: Track assessment progress per video lesson
4. **Adaptive Difficulty**: Adjust question difficulty based on previous responses
5. **Voice Response**: Support voice input for responses (integration with speech-to-text)

## Testing

To test the implementation:

1. Navigate to Video Hub in the dashboard
2. Select a track and language
3. Choose a lesson and start playing the video
4. Click "Practice Now" at any point
5. Answer the question
6. Review the evaluation and feedback
7. Acknowledge feedback if required
8. Continue with assessment or resume video

## Error Handling

The tool includes comprehensive error handling:

- **Missing Candidate**: Returns error message
- **Gemini API Unavailable**: Falls back to basic evaluation
- **JSON Parse Errors**: Handles malformed AI responses gracefully
- **Database Errors**: Logs errors and provides user-friendly messages

## Configuration

Ensure the following are configured in `config.py`:

- `GEMINI_API_KEY`: Required for AI-powered evaluation
- Database connection: For storing assessment results

