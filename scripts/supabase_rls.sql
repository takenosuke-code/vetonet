-- VetoNet Row Level Security Policies
-- Run this AFTER supabase_schema.sql
-- This protects your data from unauthorized access
--
-- IMPORTANT: The API backend uses the service_role key, which bypasses RLS.
-- These policies protect against direct Supabase access via anon/authenticated keys.

-- ============================================
-- ATTACKS TABLE
-- ============================================

ALTER TABLE attacks ENABLE ROW LEVEL SECURITY;

-- Anon/authenticated can read attacks (for public stats/feed)
CREATE POLICY "Allow select attacks"
ON attacks FOR SELECT
TO anon, authenticated
USING (true);

-- Only service_role can INSERT (API backend inserts via service key)
-- Anon/authenticated CANNOT insert directly
CREATE POLICY "Service role insert attacks"
ON attacks FOR INSERT
TO service_role
WITH CHECK (true);

-- Only service_role can UPDATE (for feedback updates from API)
CREATE POLICY "Service role update attacks"
ON attacks FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

-- No deletes except service_role
CREATE POLICY "Deny delete attacks"
ON attacks FOR DELETE
TO anon, authenticated
USING (false);

-- ============================================
-- TRAINING_DATA TABLE
-- ============================================

ALTER TABLE training_data ENABLE ROW LEVEL SECURITY;

-- Anon/authenticated can read (for model training scripts)
CREATE POLICY "Allow select training_data"
ON training_data FOR SELECT
TO anon, authenticated
USING (true);

-- Only service_role can INSERT
CREATE POLICY "Service role insert training_data"
ON training_data FOR INSERT
TO service_role
WITH CHECK (true);

-- No updates or deletes from anon/authenticated
CREATE POLICY "Deny update training_data"
ON training_data FOR UPDATE
TO anon, authenticated
USING (false);

CREATE POLICY "Deny delete training_data"
ON training_data FOR DELETE
TO anon, authenticated
USING (false);

-- ============================================
-- ML_TRAINING_DATA TABLE
-- ============================================

ALTER TABLE ml_training_data ENABLE ROW LEVEL SECURITY;

-- Anon/authenticated can read
CREATE POLICY "Allow select ml_training_data"
ON ml_training_data FOR SELECT
TO anon, authenticated
USING (true);

-- Only service_role can INSERT
CREATE POLICY "Service role insert ml_training_data"
ON ml_training_data FOR INSERT
TO service_role
WITH CHECK (true);

-- No updates or deletes from anon/authenticated
CREATE POLICY "Deny update ml_training_data"
ON ml_training_data FOR UPDATE
TO anon, authenticated
USING (false);

CREATE POLICY "Deny delete ml_training_data"
ON ml_training_data FOR DELETE
TO anon, authenticated
USING (false);

-- ============================================
-- TELEMETRY TABLE
-- ============================================

ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;

-- Anon/authenticated can read
CREATE POLICY "Allow select telemetry"
ON telemetry FOR SELECT
TO anon, authenticated
USING (true);

-- Only service_role can INSERT
CREATE POLICY "Service role insert telemetry"
ON telemetry FOR INSERT
TO service_role
WITH CHECK (true);

-- No updates or deletes
CREATE POLICY "Deny update telemetry"
ON telemetry FOR UPDATE
TO anon, authenticated
USING (false);

CREATE POLICY "Deny delete telemetry"
ON telemetry FOR DELETE
TO anon, authenticated
USING (false);

-- ============================================
-- API_KEYS TABLE (handled by migration 001)
-- ============================================
-- RLS already enabled via migrations/001_api_keys.sql
-- Users can only see their own keys (user_id = auth.uid())
-- Service role has full access

-- ============================================
-- VERIFICATION
-- ============================================
-- After running this, check that RLS shows "ENABLED" in the dashboard
-- All tables should show green "RLS enabled" badge
-- Test: Try inserting into attacks with the anon key - it should FAIL
-- Test: API backend (service_role) should still work normally
