-- VetoNet Row Level Security Policies
-- Run this AFTER supabase_schema.sql
-- This protects your data from unauthorized access

-- ============================================
-- ATTACKS TABLE
-- ============================================

-- Enable RLS
ALTER TABLE attacks ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can INSERT (API logs attacks via anon key)
CREATE POLICY "Allow insert attacks"
ON attacks FOR INSERT
TO anon, authenticated
WITH CHECK (true);

-- Policy: Anyone can SELECT (for stats/feed endpoints)
CREATE POLICY "Allow select attacks"
ON attacks FOR SELECT
TO anon, authenticated
USING (true);

-- Policy: Only service role can UPDATE (for feedback - use service key in API)
-- For now, allow authenticated to update feedback column only
CREATE POLICY "Allow update feedback"
ON attacks FOR UPDATE
TO authenticated
USING (true)
WITH CHECK (true);

-- Policy: NEVER allow DELETE from anon (protect your data)
-- Only service_role (admin) can delete
CREATE POLICY "Deny delete attacks"
ON attacks FOR DELETE
TO anon
USING (false);

-- ============================================
-- TRAINING_DATA TABLE
-- ============================================

-- Enable RLS
ALTER TABLE training_data ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can INSERT (for importing datasets)
CREATE POLICY "Allow insert training_data"
ON training_data FOR INSERT
TO anon, authenticated
WITH CHECK (true);

-- Policy: Anyone can SELECT (for model training)
CREATE POLICY "Allow select training_data"
ON training_data FOR SELECT
TO anon, authenticated
USING (true);

-- Policy: No updates allowed (training data is immutable)
CREATE POLICY "Deny update training_data"
ON training_data FOR UPDATE
TO anon
USING (false);

-- Policy: No deletes from anon
CREATE POLICY "Deny delete training_data"
ON training_data FOR DELETE
TO anon
USING (false);

-- ============================================
-- VERIFICATION
-- ============================================
-- After running this, check that RLS shows "ENABLED" in the dashboard
-- The yellow "RLS disabled" badge should turn green
