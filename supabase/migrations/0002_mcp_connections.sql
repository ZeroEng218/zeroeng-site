-- ===========================================================================
-- Build Guild — Org-level MCP connection strings
-- ---------------------------------------------------------------------------
-- Adds the per-organization registry of MCP connection URLs. Each row is an
-- outbound sender-identity channel: the URL a user plugs into their LLM
-- connector so it can send queries to Build Guild on behalf of the org. Every
-- org can register multiple (e.g. "Procurement", "Safety", "Project
-- Management"), each with a name/description so callers know what it pertains
-- to. Agents acting on behalf of the org consume these at runtime.
--
-- This is distinct from the inbound persistent-agent registry (public.agents,
-- see 0001_agents.sql). It builds on the same existing schema:
--   organizations(id uuid pk, name, role, license_number, license_jurisdiction,
--                 join_code, created_by, created_at, domain)
--   organization_members(org_id uuid, user_id uuid, email, role, status)
--
-- SECURITY MODEL
--   The application connects to Supabase with the ANON key and mediates every
--   request server-side (it validates the Supabase session cookie in Python
--   and enforces authorization there — exactly how organizations / projects /
--   agents already work in this app). RLS is enabled below and policies are
--   written for both the app's operating role and for the intended per-user
--   model, so that direct (JWT-bound) access is also constrained. service_role
--   bypasses RLS for administrative / migration use.
--
--   Per product decision, any member of the owning organization may manage
--   (create / edit / delete) that org's MCP connections — there is no
--   admin-only restriction.
-- ===========================================================================

-- ── mcp_connections ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.mcp_connections (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  name        text NOT NULL,               -- e.g. "Procurement", "Safety"
  description text,                         -- optional longer description
  url         text NOT NULL,               -- the MCP connection URL
  created_by  uuid REFERENCES auth.users(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mcp_connections_org_id_idx
  ON public.mcp_connections (org_id);

-- Keep updated_at current on every UPDATE.
CREATE OR REPLACE FUNCTION public.set_mcp_connections_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS mcp_connections_set_updated_at ON public.mcp_connections;
CREATE TRIGGER mcp_connections_set_updated_at
  BEFORE UPDATE ON public.mcp_connections
  FOR EACH ROW EXECUTE FUNCTION public.set_mcp_connections_updated_at();

-- ===========================================================================
-- Row Level Security
-- ===========================================================================
ALTER TABLE public.mcp_connections ENABLE ROW LEVEL SECURITY;

-- ---- mcp_connections : SELECT -------------------------------------------
-- Any member of the owning organization can view its connections.
DROP POLICY IF EXISTS mcp_connections_select_org_members ON public.mcp_connections;
CREATE POLICY mcp_connections_select_org_members ON public.mcp_connections
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.organization_members m
      WHERE m.org_id = mcp_connections.org_id
        AND m.user_id = auth.uid()
    )
  );

-- ---- mcp_connections : INSERT -------------------------------------------
-- Any member of the owning organization may create a connection.
DROP POLICY IF EXISTS mcp_connections_insert_org_members ON public.mcp_connections;
CREATE POLICY mcp_connections_insert_org_members ON public.mcp_connections
  FOR INSERT
  TO authenticated
  WITH CHECK (
    created_by = auth.uid()
    AND EXISTS (
      SELECT 1 FROM public.organization_members m
      WHERE m.org_id = mcp_connections.org_id
        AND m.user_id = auth.uid()
    )
  );

-- ---- mcp_connections : UPDATE -------------------------------------------
-- Any member of the owning organization may edit its connections.
DROP POLICY IF EXISTS mcp_connections_update_org_members ON public.mcp_connections;
CREATE POLICY mcp_connections_update_org_members ON public.mcp_connections
  FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.organization_members m
      WHERE m.org_id = mcp_connections.org_id
        AND m.user_id = auth.uid()
    )
  );

-- ---- mcp_connections : DELETE -------------------------------------------
-- Any member of the owning organization may delete its connections.
DROP POLICY IF EXISTS mcp_connections_delete_org_members ON public.mcp_connections;
CREATE POLICY mcp_connections_delete_org_members ON public.mcp_connections
  FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.organization_members m
      WHERE m.org_id = mcp_connections.org_id
        AND m.user_id = auth.uid()
    )
  );

-- ---- Application operating role -----------------------------------------
-- The app performs all access with the ANON key and enforces authorization in
-- Python (validated Supabase session + org-membership checks). This policy
-- lets the server operate while real authorization is enforced in the
-- application layer, mirroring the existing organizations / projects / agents
-- tables. Remove it if/when the app is migrated to bind the per-user JWT to
-- PostgREST.
DROP POLICY IF EXISTS mcp_connections_app_all ON public.mcp_connections;
CREATE POLICY mcp_connections_app_all ON public.mcp_connections
  FOR ALL TO anon
  USING (true) WITH CHECK (true);

-- service_role bypasses RLS automatically; no explicit policy required.
