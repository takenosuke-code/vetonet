-- VetoNet API Key System Migration
-- Run this in Supabase SQL Editor
-- Created: 2026-04-02

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT,
    environment TEXT NOT NULL DEFAULT 'live' CHECK (environment IN ('live', 'test')),
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    rate_limit INT DEFAULT 10000,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

-- API Usage tracking
CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint TEXT,
    timestamp TIMESTAMPTZ DEFAULT now(),
    response_status INT,
    latency_ms INT
);

CREATE INDEX IF NOT EXISTS idx_api_usage_key ON api_usage(key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_time ON api_usage(timestamp);

-- Security Audit Log
CREATE TABLE IF NOT EXISTS api_key_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    action TEXT NOT NULL,  -- created, deleted, rotated, used, failed_auth, rate_limited
    reason TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_key ON api_key_audit(key_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON api_key_audit(action);
CREATE INDEX IF NOT EXISTS idx_audit_time ON api_key_audit(created_at);

-- RLS Policies
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_audit ENABLE ROW LEVEL SECURITY;

-- Users can only see their own keys
DROP POLICY IF EXISTS "Users see own keys" ON api_keys;
CREATE POLICY "Users see own keys" ON api_keys
    FOR ALL USING (auth.uid() = user_id);

-- Users can only see usage for their own keys
DROP POLICY IF EXISTS "Users see own usage" ON api_usage;
CREATE POLICY "Users see own usage" ON api_usage
    FOR SELECT USING (key_id IN (SELECT id FROM api_keys WHERE user_id = auth.uid()));

-- Users can only see audit for their own keys
DROP POLICY IF EXISTS "Users see own audit" ON api_key_audit;
CREATE POLICY "Users see own audit" ON api_key_audit
    FOR SELECT USING (key_id IN (SELECT id FROM api_keys WHERE user_id = auth.uid()));

-- Service role can do everything (for the API server)
DROP POLICY IF EXISTS "Service role full access" ON api_keys;
CREATE POLICY "Service role full access" ON api_keys
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role usage" ON api_usage;
CREATE POLICY "Service role usage" ON api_usage
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role audit" ON api_key_audit;
CREATE POLICY "Service role audit" ON api_key_audit
    FOR ALL USING (auth.role() = 'service_role');
