-- Migration script to add detailed vocational module columns
-- Run this if you already have the database initialized

ALTER TABLE curriculum_progress
ADD COLUMN IF NOT EXISTS kaigo_basics_lessons_completed INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS kaigo_basics_total_lessons INTEGER NOT NULL DEFAULT 8,
ADD COLUMN IF NOT EXISTS communication_skills_lessons_completed INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS communication_skills_total_lessons INTEGER NOT NULL DEFAULT 6,
ADD COLUMN IF NOT EXISTS physical_care_lessons_completed INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS physical_care_total_lessons INTEGER NOT NULL DEFAULT 6;

-- Update JLPT N5 total units to 25
ALTER TABLE curriculum_progress
ALTER COLUMN jlpt_n5_total_units SET DEFAULT 25;

-- Update existing records if needed
UPDATE curriculum_progress
SET 
    kaigo_basics_lessons_completed = COALESCE(kaigo_lessons_completed, 0),
    kaigo_basics_total_lessons = 8,
    communication_skills_lessons_completed = 0,
    communication_skills_total_lessons = 6,
    physical_care_lessons_completed = 0,
    physical_care_total_lessons = 6
WHERE kaigo_basics_lessons_completed IS NULL;

-- Note: If you have an old 'kaigo_lessons_completed' column, you may need to drop it:
-- ALTER TABLE curriculum_progress DROP COLUMN IF EXISTS kaigo_lessons_completed;
-- ALTER TABLE curriculum_progress DROP COLUMN IF EXISTS kaigo_total_lessons;

