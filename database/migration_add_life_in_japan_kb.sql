-- Migration: Add life_in_japan_kb table for SupportAgent
-- Run this to create the life_in_japan_kb table

CREATE TABLE IF NOT EXISTS life_in_japan_kb (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en' NOT NULL,
    source VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_life_in_japan_kb_topic ON life_in_japan_kb(topic);
CREATE INDEX IF NOT EXISTS idx_life_in_japan_kb_category ON life_in_japan_kb(category);
CREATE INDEX IF NOT EXISTS idx_life_in_japan_kb_language ON life_in_japan_kb(language);

-- Add comment for documentation
COMMENT ON TABLE life_in_japan_kb IS 'Knowledge base for legal/personal advice about life in Japan (used by SupportAgent)';

