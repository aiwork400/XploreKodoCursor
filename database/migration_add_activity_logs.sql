-- Migration: Add activity_logs table for Admin Monitoring Center
-- Run this to create the activity_logs table

CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    event_metadata JSONB,
    message TEXT
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_event_type ON activity_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_activity_logs_severity ON activity_logs(severity);

-- Composite index for common queries (recent warnings/errors)
CREATE INDEX IF NOT EXISTS idx_activity_logs_severity_timestamp ON activity_logs(severity, timestamp DESC);

COMMENT ON TABLE activity_logs IS 'Tracks all system events for admin monitoring and audit purposes';
COMMENT ON COLUMN activity_logs.event_type IS 'Type of event: Grading, Briefing, Error, API_Call, etc.';
COMMENT ON COLUMN activity_logs.severity IS 'Severity level: Info, Warning, Error';
COMMENT ON COLUMN activity_logs.event_metadata IS 'JSON data with event-specific details (transcript, score, API response, etc.)';

