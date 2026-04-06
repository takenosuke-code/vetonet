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
    source VARCHAR(100),        -- origin of the attack data

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

-- API keys for SDK authentication
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    key_hash TEXT,
    key_prefix VARCHAR(20),
    name VARCHAR(100),
    rate_limit INT DEFAULT 10000,
    is_active BOOLEAN DEFAULT true,
    environment VARCHAR(10) DEFAULT 'live',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

-- API usage tracking
CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id UUID REFERENCES api_keys(id),
    endpoint VARCHAR(100),
    response_status INT,
    latency_ms INT,
    timestamp TIMESTAMPTZ DEFAULT now()
);

-- API key audit log
CREATE TABLE IF NOT EXISTS api_key_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id UUID,
    user_id UUID,
    action VARCHAR(50),
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ML training data (structured for model training pipelines)
CREATE TABLE IF NOT EXISTS ml_training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT,
    intent JSONB,
    payload JSONB,
    label INT,
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Telemetry for monitoring and observability
CREATE TABLE IF NOT EXISTS telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50),
    category VARCHAR(50),
    verdict VARCHAR(20),
    checks_passed JSONB,
    checks_failed JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_attacks_created_at ON attacks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attacks_verdict ON attacks(verdict);
CREATE INDEX IF NOT EXISTS idx_attacks_feedback ON attacks(feedback) WHERE feedback IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_attacks_type ON attacks(type);
CREATE INDEX IF NOT EXISTS idx_training_source ON training_data(source);
CREATE INDEX IF NOT EXISTS idx_training_is_attack ON training_data(is_attack);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_usage(key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_key_audit_key_id ON api_key_audit(key_id);
CREATE INDEX IF NOT EXISTS idx_ml_training_data_source ON ml_training_data(source);
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_source ON telemetry(source);

-- Enable Row Level Security (optional, for multi-tenant future)
-- ALTER TABLE attacks ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE training_data ENABLE ROW LEVEL SECURITY;

-- Grant access: anon gets read-only on public data, authenticated gets read-write
-- SECURITY: api_keys table is service_role only (no anon/authenticated write access)
GRANT SELECT, INSERT ON attacks TO anon, authenticated;
GRANT UPDATE ON attacks TO authenticated;
GRANT SELECT, INSERT ON training_data TO anon, authenticated;
GRANT SELECT ON api_keys TO authenticated;
GRANT SELECT, INSERT ON api_usage TO authenticated;
GRANT SELECT, INSERT ON api_key_audit TO authenticated;
GRANT SELECT, INSERT ON ml_training_data TO authenticated;
GRANT SELECT, INSERT ON telemetry TO anon, authenticated;

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
