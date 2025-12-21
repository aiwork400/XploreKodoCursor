-- Migration: Add baseline_assessment_results column to curriculum_progress table
-- Run this to add the baseline assessment field

ALTER TABLE curriculum_progress 
ADD COLUMN IF NOT EXISTS baseline_assessment_results JSON;

-- Add comment for documentation
COMMENT ON COLUMN curriculum_progress.baseline_assessment_results IS 'Stores initial 5-question baseline assessment results as JSON: {"assessment_date": "...", "overall_score": ..., "questions": [...]}';

