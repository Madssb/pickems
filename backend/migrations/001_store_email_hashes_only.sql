-- Run with:
-- psql "$DATABASE_URL" -v email_hash_secret="$EMAIL_HASH_SECRET" -f backend/migrations/001_store_email_hashes_only.sql
--
-- This migrates the old users.email column to users.email_hash, then drops
-- the raw email values from the database.

\if :{?email_hash_secret}
\else
  \echo 'email_hash_secret is required. Pass -v email_hash_secret="$EMAIL_HASH_SECRET"'
  \quit 1
\endif

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE users
ADD COLUMN email_hash TEXT;

UPDATE users
SET email_hash = encode(
    hmac(
        lower(trim(email)),
        :'email_hash_secret',
        'sha256'
    ),
    'hex'
)
WHERE email_hash IS NULL;

ALTER TABLE users
ALTER COLUMN email_hash SET NOT NULL;

ALTER TABLE users
ADD CONSTRAINT users_email_hash_key UNIQUE (email_hash);

ALTER TABLE users
DROP CONSTRAINT users_email_key;

ALTER TABLE users
DROP COLUMN email;

COMMIT;
