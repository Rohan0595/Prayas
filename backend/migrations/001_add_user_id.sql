-- Migration: Add user_id to sessions for user-scoped chat history
-- Run this in your Supabase dashboard → SQL Editor

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Tag existing sessions as 'legacy' so they don't show for new users
UPDATE sessions SET user_id = 'legacy' WHERE user_id IS NULL;
