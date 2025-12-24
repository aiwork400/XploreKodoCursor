-- Migration: Add syllabus table for Triple-Track Coaching video lessons
-- Run this to create the syllabus table for managing video content across tracks

-- Syllabus table for video lessons
CREATE TABLE IF NOT EXISTS syllabus (
    id SERIAL PRIMARY KEY,
    
    -- Track classification
    track VARCHAR(50) NOT NULL,
    
    -- Lesson metadata
    lesson_title VARCHAR(500) NOT NULL,
    lesson_description TEXT,
    lesson_number INTEGER NOT NULL DEFAULT 1,
    
    -- Video file information
    video_path VARCHAR(1000) NOT NULL,
    video_filename VARCHAR(500) NOT NULL,
    
    -- Language support (for multi-language video versions)
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    
    -- Topic for Socratic Assessment
    topic VARCHAR(200),
    
    -- Lesson metadata
    duration_minutes INTEGER,
    difficulty_level VARCHAR(20),
    
    -- Ordering and organization
    module_name VARCHAR(200),
    sequence_order INTEGER NOT NULL DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_syllabus_track ON syllabus(track);
CREATE INDEX IF NOT EXISTS idx_syllabus_language ON syllabus(language);
CREATE INDEX IF NOT EXISTS idx_syllabus_sequence_order ON syllabus(sequence_order);
CREATE INDEX IF NOT EXISTS idx_syllabus_track_language ON syllabus(track, language);

-- Add comments for documentation
COMMENT ON TABLE syllabus IS 'Manages video lessons and curriculum content for Triple-Track Coaching (Care-giving, Academic, Food/Tech)';
COMMENT ON COLUMN syllabus.track IS 'Track type: Care-giving, Academic, or Food/Tech';
COMMENT ON COLUMN syllabus.language IS 'Language code: en, ja, or ne';
COMMENT ON COLUMN syllabus.topic IS 'Topic identifier for triggering Socratic Assessment (e.g., omotenashi, knowledge_base)';
COMMENT ON COLUMN syllabus.video_path IS 'Relative path to video file in assets/videos/{track}/';

