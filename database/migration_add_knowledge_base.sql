-- Migration: Add knowledge_base table for storing PDF-extracted caregiving concepts
-- Run this to create the knowledge base table

-- Knowledge base table
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    source_file VARCHAR(500) NOT NULL,
    concept_title VARCHAR(500) NOT NULL,
    concept_content TEXT NOT NULL,
    page_number INTEGER,
    language VARCHAR(10) NOT NULL DEFAULT 'ja',
    category VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for knowledge base
CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_language ON knowledge_base(language);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_source_file ON knowledge_base(source_file);

-- Add comment
COMMENT ON TABLE knowledge_base IS 'Stores extracted content from caregiving training PDFs for Socratic questioning';

