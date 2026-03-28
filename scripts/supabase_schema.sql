-- VetoNet Supabase Schema
-- Run this in the Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- Main attacks table (enhanced for ML training)
CREATE TABLE IF NOT EXISTS attacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Request data
    type VARCHAR(50),           -- demo, redteam, sdk, fuzzer
    prompt TEXT,
    intent JSONB,               -- normalized intent from user
    payload JSONB,              -- agent's proposed transaction

    -- Result data
    verdict VARCHAR(20),        -- approved, blocked
    blocked_by VARCHAR(50),     -- which check caught it
    checks JSONB,               -- all check results with scores
    confidence FLOAT,           -- LLM confidence score (0-1)
    reasoning TEXT,             -- LLM reasoning text

    -- Attack classification
    attack_vector VARCHAR(100), -- hidden_fees, semantic_bypass, etc.

    -- User feedback (GOLD for training)
    feedback VARCHAR(20),       -- correct, false_positive, false_negative
    feedback_at TIMESTAMPTZ
);

-- Training data from external sources (Kaggle, etc.)
CREATE TABLE IF NOT EXISTS training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(100),        -- kaggle_cyberprince, kaggle_aestera, internal
    prompt TEXT NOT NULL,
    is_attack BOOLEAN NOT NULL,
    attack_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_attacks_created_at ON attacks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attacks_verdict ON attacks(verdict);
CREATE INDEX IF NOT EXISTS idx_attacks_feedback ON attacks(feedback) WHERE feedback IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_attacks_type ON attacks(type);
CREATE INDEX IF NOT EXISTS idx_training_source ON training_data(source);
CREATE INDEX IF NOT EXISTS idx_training_is_attack ON training_data(is_attack);

-- Enable Row Level Security (optional, for multi-tenant future)
-- ALTER TABLE attacks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE training_data ENABLE ROW LEVEL SECURITY;

-- Grant access to anon and authenticated roles
GRANT SELECT, INSERT, UPDATE ON attacks TO anon, authenticated;
GRANT SELECT, INSERT ON training_data TO anon, authenticated;

-- Useful views

-- View: Recent attacks with feedback
CREATE OR REPLACE VIEW recent_attacks_with_feedback AS
SELECT
    id,
    created_at,
    type,
    prompt,
    verdict,
    blocked_by,
    confidence,
    feedback,
    attack_vector
FROM attacks
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- View: Feedback stats
CREATE OR REPLACE VIEW feedback_stats AS
SELECT
    feedback,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM attacks
WHERE feedback IS NOT NULL
GROUP BY feedback;

-- View: Attack vector stats
CREATE OR REPLACE VIEW attack_vector_stats AS
SELECT
    attack_vector,
    COUNT(*) as total,
    SUM(CASE WHEN verdict = 'approved' THEN 1 ELSE 0 END) as bypassed,
    SUM(CASE WHEN verdict = 'blocked' THEN 1 ELSE 0 END) as blocked
FROM attacks
WHERE attack_vector IS NOT NULL
GROUP BY attack_vector
ORDER BY total DESC;
