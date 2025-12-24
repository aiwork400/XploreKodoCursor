# Triple-Track Coaching System Implementation

## Overview

This document describes the implementation of the Triple-Track Coaching model supporting three distinct learning tracks:
- **Care-giving** (Kaigo Training)
- **Academic** (Academic Preparation)
- **Food/Tech** (Technology and Food Industry Training)

## Components Implemented

### 1. Syllabus Model (`models/curriculum.py`)

The `Syllabus` model manages video lessons and curriculum content across all three tracks:

- **Track Classification**: Each lesson is tagged with a track (`Care-giving`, `Academic`, or `Food/Tech`)
- **Multi-language Support**: Lessons can have versions in English (`en`), Japanese (`ja`), or Nepali (`ne`)
- **Socratic Assessment Integration**: Each lesson can specify a `topic` for triggering Socratic questioning
- **Metadata**: Includes lesson number, title, description, duration, difficulty level, and module organization

### 2. Video Hub (`dashboard/app.py`)

The Video Hub page provides:

- **Track Selection**: Radio buttons to choose between the three coaching tracks
- **Language Toggle**: Switch between English, Japanese, and Nepali video versions
- **Dynamic Video Loading**: 
  - First attempts to load from database (Syllabus model)
  - Falls back to file system scanning if database is empty
- **Video Player**: Native Streamlit `st.video` widget for playback
- **Practice Now Button**: Triggers Socratic Assessment based on the current lesson's topic

### 3. JSON-Based Event Listener

The Video Hub includes a JavaScript-based event system:

- **Event Data Storage**: Lesson metadata (track, language, topic, lesson ID) stored in `window.videoHubEventData`
- **Video Play Events**: Listens for video play events for future browser-side integration
- **Practice Now Integration**: Button triggers Socratic Assessment with the lesson's topic

### 4. Track-Based TTS Voice Personality (`config.py`)

Enhanced TTS system with personality adjustments based on track:

- **Care-giving**: Gentle tone (lower pitch, slower rate, female voice preference)
- **Academic**: Formal tone (neutral pitch, standard rate, neutral voice)
- **Food/Tech**: Professional tone (slightly higher pitch, faster rate, neutral voice)

The `generate_trilingual_tts()` function now accepts an optional `track` parameter to apply these personality settings.

### 5. Database Migration (`database/migration_add_syllabus.sql`)

SQL migration script to create the `syllabus` table with:
- Track and language indexes for efficient querying
- Support for video file paths and metadata
- Topic field for Socratic Assessment integration

## Directory Structure

```
assets/
└── videos/
    ├── kaigo/          # Care-giving videos
    ├── academic/       # Academic videos
    └── tech/           # Food/Tech videos
```

## Usage

### Adding Videos

1. **Via File System**: Place video files (`.mp4`, `.webm`, `.ogg`) in the appropriate track directory
2. **Via Database**: Use the Syllabus model to add structured lesson data:

```python
from models.curriculum import Syllabus
from database.db_manager import SessionLocal

db = SessionLocal()
lesson = Syllabus(
    track="Care-giving",
    lesson_title="Introduction to Kaigo Basics",
    lesson_description="Learn the fundamentals of caregiving",
    lesson_number=1,
    video_path="assets/videos/kaigo/intro_lesson_1.mp4",
    video_filename="intro_lesson_1.mp4",
    language="en",
    topic="omotenashi",
    duration_minutes=15,
    difficulty_level="Beginner",
    module_name="Kaigo Basics",
    sequence_order=1
)
db.add(lesson)
db.commit()
```

### Using the Video Hub

1. Navigate to **Video Hub** in the dashboard
2. Select your track (Care-giving, Academic, or Food/Tech)
3. Choose your preferred language (English, Japanese, or Nepali)
4. Select a lesson from the dropdown
5. Watch the video
6. Click **Practice Now** to start a Socratic Assessment based on the lesson's topic

### TTS with Track Personality

```python
from dashboard.app import generate_trilingual_tts

# Care-giving track - gentle tone
audio = generate_trilingual_tts(
    text="Welcome to caregiving training",
    language="en",
    track="Care-giving"
)

# Academic track - formal tone
audio = generate_trilingual_tts(
    text="Let's begin the academic lesson",
    language="en",
    track="Academic"
)
```

## Database Setup

Run the migration script to create the syllabus table:

```bash
psql -U postgres -d xplorekodo -f database/migration_add_syllabus.sql
```

Or use Python:

```python
from database.db_manager import engine
from models.curriculum import Syllabus

# Ensure Syllabus model is imported
Syllabus.metadata.create_all(bind=engine)
```

## Future Enhancements

- Video progress tracking per candidate
- Playlist creation and management
- Video annotations and notes
- Integration with Virtual Classroom avatar
- Real-time video analytics
- Multi-language subtitle support

## Notes

- The Video Hub automatically detects videos from the file system if the database is empty
- Socratic Assessment requires a valid `candidate_id` to track progress
- TTS personality settings are applied automatically when a track is specified
- All three languages (English, Japanese, Nepali) are supported across all tracks

