-- Migration script to add simulation_performance column
-- Run this if you already have the database initialized

ALTER TABLE curriculum_progress
ADD COLUMN IF NOT EXISTS simulation_performance TEXT;

COMMENT ON COLUMN curriculum_progress.simulation_performance IS 'Stored Kaigo simulation scores in format: scenario_type:score;scenario_type:score';

