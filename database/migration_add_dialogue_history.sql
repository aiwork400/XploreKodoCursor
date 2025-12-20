-- Migration: Add dialogue_history JSONB column to curriculum_progress table
-- Run this if you have an existing database without the dialogue_history column

-- Add dialogue_history JSONB column
ALTER TABLE curriculum_progress 
ADD COLUMN IF NOT EXISTS dialogue_history JSONB;

-- Add comment for documentation
COMMENT ON COLUMN curriculum_progress.dialogue_history IS 'Stores all Socratic questioning interactions: [{"question": {...}, "answer": "...", "timestamp": "..."}, ...]';

