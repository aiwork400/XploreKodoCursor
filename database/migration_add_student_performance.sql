-- Migration: Add student_performance table for Memory Layer and RAG-based curriculum
-- Run this to create the student performance tracking table

-- Student performance table
CREATE TABLE IF NOT EXISTS student_performance (
    id SERIAL PRIMARY KEY,
    candidate_id VARCHAR(100) NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    word_id INTEGER REFERENCES knowledge_base(id) ON DELETE SET NULL,
    word_title VARCHAR(500),  -- Denormalized for quick access (from knowledge_base.concept_title)
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 10),
    feedback TEXT,
    accuracy_feedback TEXT,
    grammar_feedback TEXT,
    pronunciation_hint TEXT,
    transcript TEXT,  -- The candidate's transcribed answer
    language_code VARCHAR(10) DEFAULT 'ja-JP',
    category VARCHAR(100),  -- e.g., 'jlpt_n5_vocabulary', 'caregiving_vocabulary'
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance queries
CREATE INDEX IF NOT EXISTS idx_student_performance_candidate_id ON student_performance(candidate_id);
CREATE INDEX IF NOT EXISTS idx_student_performance_word_id ON student_performance(word_id);
CREATE INDEX IF NOT EXISTS idx_student_performance_category ON student_performance(category);
CREATE INDEX IF NOT EXISTS idx_student_performance_created_at ON student_performance(created_at);
CREATE INDEX IF NOT EXISTS idx_student_performance_candidate_category ON student_performance(candidate_id, category);

-- Add comment for documentation
COMMENT ON TABLE student_performance IS 'Tracks individual word/concept performance for RAG-based curriculum prioritization';
COMMENT ON COLUMN student_performance.word_id IS 'Reference to knowledge_base.id (can be NULL if word not in knowledge_base)';
COMMENT ON COLUMN student_performance.word_title IS 'Denormalized word title for quick access without joins';
COMMENT ON COLUMN student_performance.score IS 'Grade from 1-10 based on accuracy and grammar';

