-- Migration: Add mastery_scores column to curriculum_progress table
-- Stores mastery scores per track and skill category as JSON
-- Format: {"Food/Tech": {"Vocabulary": 75.0, "Tone/Honorifics": 60.0, "Contextual Logic": 80.0}, ...}

ALTER TABLE curriculum_progress 
ADD COLUMN IF NOT EXISTS mastery_scores JSON;

-- Add comment for documentation
COMMENT ON COLUMN curriculum_progress.mastery_scores IS 'Stores mastery scores (0-100) per track and skill category as JSON: {"Food/Tech": {"Vocabulary": 75.0, "Tone/Honorifics": 60.0, "Contextual Logic": 80.0}, "Academic": {...}, "Care-giving": {...}}';

