-- XploreKodo PostgreSQL 16 Database Initialization Script
-- Creates tables for candidates, document_vault, curriculum_progress, and payments

-- Create database (run this separately if needed)
-- CREATE DATABASE xplorekodo;

-- Connect to database
-- \c xplorekodo;

-- Enable UUID extension (if needed in future)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Candidates table
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id VARCHAR(100) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    track VARCHAR(20) NOT NULL CHECK (track IN ('student', 'jobseeker')),
    
    -- Document paths
    passport_path VARCHAR(500),
    coe_path VARCHAR(500),
    transcripts_paths TEXT,  -- JSON array as text
    
    -- Student-specific requirements
    has_150_hour_study_certificate BOOLEAN NOT NULL DEFAULT FALSE,
    has_financial_sponsor_docs BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Jobseeker-specific requirements (Japan corridor)
    has_jlpt_n4_or_n5 BOOLEAN NOT NULL DEFAULT FALSE,
    has_kaigo_skills_test BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Status fields
    status VARCHAR(50) NOT NULL DEFAULT 'Incomplete',
    travel_ready BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Document vault table
CREATE TABLE IF NOT EXISTS document_vault (
    id SERIAL PRIMARY KEY,
    candidate_id VARCHAR(100) NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    doc_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(candidate_id, doc_type)  -- One document per type per candidate
);

-- Curriculum progress table
CREATE TABLE IF NOT EXISTS curriculum_progress (
    id SERIAL PRIMARY KEY,
    candidate_id VARCHAR(100) NOT NULL UNIQUE REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    
    -- Language progress (JLPT N5/N4/N3)
    jlpt_n5_units_completed INTEGER NOT NULL DEFAULT 0,
    jlpt_n5_total_units INTEGER NOT NULL DEFAULT 25,  -- Updated to 25 units as specified
    jlpt_n4_units_completed INTEGER NOT NULL DEFAULT 0,
    jlpt_n4_total_units INTEGER NOT NULL DEFAULT 40,
    jlpt_n3_units_completed INTEGER NOT NULL DEFAULT 0,
    jlpt_n3_total_units INTEGER NOT NULL DEFAULT 50,
    
    -- Vocational progress (Kaigo) - Detailed modules
    kaigo_basics_lessons_completed INTEGER NOT NULL DEFAULT 0,
    kaigo_basics_total_lessons INTEGER NOT NULL DEFAULT 8,
    communication_skills_lessons_completed INTEGER NOT NULL DEFAULT 0,
    communication_skills_total_lessons INTEGER NOT NULL DEFAULT 6,
    physical_care_lessons_completed INTEGER NOT NULL DEFAULT 0,
    physical_care_total_lessons INTEGER NOT NULL DEFAULT 6,
    kaigo_certification_status VARCHAR(50) NOT NULL DEFAULT 'In Progress',
    
    -- Professional progress (AI/ML)
    ai_ml_topics_completed INTEGER NOT NULL DEFAULT 0,
    ai_ml_total_topics INTEGER NOT NULL DEFAULT 15,
    ai_ml_project_status VARCHAR(50) NOT NULL DEFAULT 'In Progress',
    
    -- Phase 2: AR-VR hooks (dormant)
    ar_vr_sessions_completed INTEGER NOT NULL DEFAULT 0,
    ar_vr_last_session TIMESTAMP,
    
    -- Kaigo Simulation Performance
    simulation_performance TEXT,
    
    -- Socratic Dialogue History (JSONB)
    -- Stores all Socratic questioning interactions: [{"question": {...}, "answer": "...", "timestamp": "..."}, ...]
    dialogue_history JSONB,
    
    -- Timestamps
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    candidate_id VARCHAR(100) NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    amount VARCHAR(20) NOT NULL,  -- Store as string to preserve precision
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    provider VARCHAR(20) NOT NULL CHECK (provider IN ('stripe', 'paypal')),
    transaction_id VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed')),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_travel_ready ON candidates(travel_ready);
CREATE INDEX IF NOT EXISTS idx_candidates_track ON candidates(track);
CREATE INDEX IF NOT EXISTS idx_document_vault_candidate_id ON document_vault(candidate_id);
CREATE INDEX IF NOT EXISTS idx_payments_candidate_id ON payments(candidate_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_candidates_updated_at BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_curriculum_progress_updated_at BEFORE UPDATE ON curriculum_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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

-- Comments for documentation
COMMENT ON TABLE candidates IS 'Core candidate profiles for XploreKodo Journey Core';
COMMENT ON TABLE document_vault IS 'Secure file path references for candidate documents';
COMMENT ON TABLE curriculum_progress IS 'Tracks candidate progress across Language, Vocational, and Professional modules';
COMMENT ON TABLE knowledge_base IS 'Stores extracted content from caregiving training PDFs for Socratic questioning';
COMMENT ON TABLE payments IS 'Payment transactions for fee collection';

COMMENT ON COLUMN candidates.has_150_hour_study_certificate IS 'Student track: 150-hour study certificate requirement';
COMMENT ON COLUMN candidates.has_jlpt_n4_or_n5 IS 'Jobseeker track: JLPT N4/N5 certificate requirement';
COMMENT ON COLUMN candidates.has_kaigo_skills_test IS 'Jobseeker track: Kaigo Skills Test requirement';

