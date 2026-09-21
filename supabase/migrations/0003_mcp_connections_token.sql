-- ===========================================================================
-- Build Guild — MCP connections: website-minted connection URLs
-- ---------------------------------------------------------------------------
-- Previously the connection URL was typed in by the user. Build Guild now MINTS
-- a unique, identity-bearing URL for every MCP connection: on create it stores a
-- random url-safe `token` and sets `url` to
--     https://www.zeroeng.io/build-guild/mcp/<token>
-- which resolves (GET) to the org identity that owns the connection. The token
-- is immutable so connectors already wired to a URL keep working.
--
-- This migration adds the `token` column, backfills any pre-existing rows with a
-- freshly minted token + resolver URL, and enforces token uniqueness. It is
-- idempotent and safe to re-run.
-- ===========================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Add the token column (nullable; the app always sets it on insert).
ALTER TABLE public.mcp_connections
  ADD COLUMN IF NOT EXISTS token text;

-- 2. Backfill a unique url-safe token for any row that predates this change.
--    gen_random_bytes is volatile, so each row gets a distinct value. 24 bytes
--    base64-encodes to 32 chars with no padding; translate makes it url-safe.
UPDATE public.mcp_connections
SET token = translate(encode(gen_random_bytes(24), 'base64'), '+/', '-_')
WHERE token IS NULL;

-- 3. Repoint pre-existing rows at their newly minted resolver URL so the whole
--    table follows the same model (each URL resolves via its token). Rows that
--    were already created through the new minting path are left untouched.
UPDATE public.mcp_connections
SET url = 'https://www.zeroeng.io/build-guild/mcp/' || token
WHERE token IS NOT NULL
  AND (url IS NULL OR url NOT LIKE '%/build-guild/mcp/%');

-- 4. Enforce uniqueness and make token lookups (the resolver) fast.
CREATE UNIQUE INDEX IF NOT EXISTS mcp_connections_token_key
  ON public.mcp_connections (token);
