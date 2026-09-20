-- ===========================================================================
-- Build Guild — Agent integration schema
-- ---------------------------------------------------------------------------
-- Adds the firm/agent registry that lets each organization register the
-- persistent agent(s) it operates on its own infrastructure, plus per-project
-- agents, plus a lightweight message log for the /messages relay threads.
--
-- Notes on the existing schema this builds on (already provisioned in the
-- active Supabase project):
--   organizations(id uuid pk, name, role, license_number, license_jurisdiction,
--                 join_code, created_by, created_at)
--   organization_members(org_id uuid, user_id uuid, email, role, status)
--   projects(id uuid pk, name, description, location, owner_id, created_at)
--   project_members(project_id uuid, user_id uuid, email, role, status)
--
-- SECURITY MODEL
--   The application connects to Supabase with the ANON key and mediates every
--   request server-side (it validates the Supabase session cookie in Python
--   and enforces authorization there — exactly how organizations / projects
--   already work in this app). RLS is enabled below and policies are written
--   for both the app's operating role and for the intended per-user model, so
--   that direct (JWT-bound) access is also constrained. service_role bypasses
--   RLS for administrative / migration use.
-- ===========================================================================

-- ── Domain auto-grouping ────────────────────────────────────────────────
-- Email domain -> organization. Set when an org is created; used to auto-join
-- new users whose email domain matches an existing organization.
ALTER TABLE public.organizations
  ADD COLUMN IF NOT EXISTS domain text;

CREATE INDEX IF NOT EXISTS organizations_domain_idx
  ON public.organizations (lower(domain));

-- ── Enums ──────────────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_type') THEN
    CREATE TYPE agent_type AS ENUM ('company', 'project');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_status') THEN
    CREATE TYPE agent_status AS ENUM ('pending', 'approved', 'offline');
  END IF;
END$$;

-- ── agents ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.agents (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name           text NOT NULL,
  type           agent_type NOT NULL,
  org_id         uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  project_id     uuid REFERENCES public.projects(id) ON DELETE CASCADE, -- NULL for company agents
  created_by     uuid NOT NULL REFERENCES auth.users(id),
  agent_url      text NOT NULL,
  discovery_card jsonb,
  status         agent_status NOT NULL DEFAULT 'pending',
  approved_at    timestamptz,
  last_ping      timestamptz,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agents_org_id_idx     ON public.agents (org_id);
CREATE INDEX IF NOT EXISTS agents_project_id_idx ON public.agents (project_id);

-- ── agent_messages ─────────────────────────────────────────────────────
-- Persisted chat-thread history for the /messages relay. A "conversation" is
-- keyed by conversation_id (returned by the remote agent) so a thread can be
-- continued across page loads.
CREATE TABLE IF NOT EXISTS public.agent_messages (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id        uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  project_id      uuid REFERENCES public.projects(id) ON DELETE CASCADE,
  conversation_id text,
  sender          text NOT NULL,        -- 'user' | 'agent'
  from_firm       text,
  body            text NOT NULL,
  created_by      uuid REFERENCES auth.users(id),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_messages_agent_id_idx
  ON public.agent_messages (agent_id, created_at);
CREATE INDEX IF NOT EXISTS agent_messages_conversation_idx
  ON public.agent_messages (conversation_id);

-- ===========================================================================
-- Row Level Security
-- ===========================================================================
ALTER TABLE public.agents         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_messages ENABLE ROW LEVEL SECURITY;

-- Helper predicates are inlined in each policy. Membership is resolved through
-- organization_members / project_members exactly like the rest of the app.

-- ---- agents : SELECT ----------------------------------------------------
-- Any member of the owning organization can view its agents.
DROP POLICY IF EXISTS agents_select_org_members ON public.agents;
CREATE POLICY agents_select_org_members ON public.agents
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.organization_members m
      WHERE m.org_id = agents.org_id
        AND m.user_id = auth.uid()
    )
  );

-- ---- agents : INSERT ----------------------------------------------------
-- Company agents: only Admins of the owning org may create.
-- Project agents: any member of the referenced project may create.
DROP POLICY IF EXISTS agents_insert_company_admin ON public.agents;
CREATE POLICY agents_insert_company_admin ON public.agents
  FOR INSERT
  TO authenticated
  WITH CHECK (
    created_by = auth.uid()
    AND (
      (
        type = 'company'
        AND project_id IS NULL
        AND EXISTS (
          SELECT 1 FROM public.organization_members m
          WHERE m.org_id = agents.org_id
            AND m.user_id = auth.uid()
            AND lower(m.role) = 'admin'
        )
      )
      OR
      (
        type = 'project'
        AND project_id IS NOT NULL
        AND (
          EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = agents.project_id
              AND p.owner_id = auth.uid()
          )
          OR EXISTS (
            SELECT 1 FROM public.project_members pm
            WHERE pm.project_id = agents.project_id
              AND pm.user_id = auth.uid()
          )
        )
      )
    )
  );

-- ---- agents : UPDATE ----------------------------------------------------
-- Org admins may update company agents; project members (or the org admin)
-- may update project agents for their project.
DROP POLICY IF EXISTS agents_update_authorized ON public.agents;
CREATE POLICY agents_update_authorized ON public.agents
  FOR UPDATE
  TO authenticated
  USING (
    (
      type = 'company'
      AND EXISTS (
        SELECT 1 FROM public.organization_members m
        WHERE m.org_id = agents.org_id
          AND m.user_id = auth.uid()
          AND lower(m.role) = 'admin'
      )
    )
    OR
    (
      type = 'project'
      AND (
        EXISTS (
          SELECT 1 FROM public.projects p
          WHERE p.id = agents.project_id AND p.owner_id = auth.uid()
        )
        OR EXISTS (
          SELECT 1 FROM public.project_members pm
          WHERE pm.project_id = agents.project_id AND pm.user_id = auth.uid()
        )
        OR EXISTS (
          SELECT 1 FROM public.organization_members m
          WHERE m.org_id = agents.org_id
            AND m.user_id = auth.uid()
            AND lower(m.role) = 'admin'
        )
      )
    )
  );

-- ---- agent_messages : SELECT / INSERT -----------------------------------
-- Visible to members of the agent's org; insertable by the same.
DROP POLICY IF EXISTS agent_messages_select_org ON public.agent_messages;
CREATE POLICY agent_messages_select_org ON public.agent_messages
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.agents a
      JOIN public.organization_members m ON m.org_id = a.org_id
      WHERE a.id = agent_messages.agent_id
        AND m.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS agent_messages_insert_org ON public.agent_messages;
CREATE POLICY agent_messages_insert_org ON public.agent_messages
  FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.agents a
      JOIN public.organization_members m ON m.org_id = a.org_id
      WHERE a.id = agent_messages.agent_id
        AND m.user_id = auth.uid()
    )
  );

-- ---- Application operating role -----------------------------------------
-- The app performs all access with the ANON key and enforces authorization in
-- Python (validated Supabase session + role checks). These policies let the
-- server operate while real authorization is enforced in the application
-- layer, mirroring the existing organizations / projects tables. Remove these
-- if/when the app is migrated to bind the per-user JWT to PostgREST.
DROP POLICY IF EXISTS agents_app_all ON public.agents;
CREATE POLICY agents_app_all ON public.agents
  FOR ALL TO anon
  USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS agent_messages_app_all ON public.agent_messages;
CREATE POLICY agent_messages_app_all ON public.agent_messages
  FOR ALL TO anon
  USING (true) WITH CHECK (true);

-- service_role bypasses RLS automatically; no explicit policy required.
