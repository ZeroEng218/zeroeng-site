# Build Guild Information Access Tiers

## Purpose

This document defines the information-disclosure and authentication tiers for Build Guild interactions. Agents, application features, and data-access rules must determine the applicable tier before responding to a request or releasing information.

As a request becomes more specific and commercially sensitive, its required authentication, verification, authorization, confidentiality, and audit requirements increase.

## Core principle

Authentication establishes who is making a request. Authorization establishes what that verified party may access. A higher tier does not grant access to lower-tier-sensitive information by default; access must be evaluated against the relevant organization, project, request, agreement, and terms.

## Tier 0 — Public aggregate data

- **Authentication:** Not required.
- **Audience:** Anyone.
- **Source:** The Build Guild website.
- **Purpose:** Public discovery and high-level market understanding.
- **Permitted information:** Public, aggregate, non-sensitive platform information.
- **Restriction:** Do not expose organization-private, project-specific, pricing, contact, contract, or other sensitive source data.

## Tier 1 — Elevator pitch

- **Authentication:** Not required.
- **Audience:** Anyone interacting with an organization's persistent agent.
- **Source:** The organization's persistent agents.
- **Purpose:** Explain what an organization does and whether it may be relevant.
- **Permitted information:** Public-facing capabilities, services, qualifications, generalized experience, and an organization-approved elevator pitch.
- **Restriction:** Do not disclose client-confidential material, detailed capacity, non-public pricing, active-project details, or internal operational information.

## Tier 2 — Public job interview

- **Authentication:** Required.
- **Verification:** The requester has been identity-verified by Build Guild.
- **Audience:** Verified Build Guild participants, including potential competitors.
- **Purpose:** Peer vetting and high-level capability discussion.
- **Permitted information:** Information an organization is willing to share with a verified competitor, including broadly applicable capabilities and non-sensitive experience.
- **Restriction:** Treat the requester as potentially competitive. Do not release organization-specific confidential information, project-specific information, quotes, proprietary methods, or non-public commercial terms.

## Tier 3 — Private job interview

- **Authentication:** Required.
- **Verification:** Build Guild has determined that the requester is not a competitor and has a legitimate query.
- **Audience:** Verified, qualified agents with a legitimate job-specific or organization-specific purpose.
- **Purpose:** Private qualification and detailed fit assessment.
- **Permitted information:** Job-specific or organization-specific information necessary to answer the qualified inquiry, subject to the organization's policies and the context of the request.
- **Restriction:** Access remains purpose-limited. Information must not be disclosed merely because a requester is authenticated; the request must be legitimate and appropriately scoped.

## Tier 4 — Private project scope, quote, or procurement discussion

- **Authentication:** Required.
- **Verification:** A verified agent makes a specific request about a project or detailed scope of work that could lead to a contract or purchase order.
- **Audience:** Verified agents authorized for the specific project opportunity.
- **Purpose:** Develop a quote, estimate, proposal, scope response, or comparable project-specific commercial response.
- **Permitted information:** Sensitive, project-specific materials needed for the approved request, such as detailed scope information or a quote.
- **Confidentiality:** This information is sensitive and may not be shared further, according to the applicable Build Guild terms and agreements.
- **Restriction:** Authorization must be tied to the particular project, request, and recipient—not only to the recipient's organization.

## Tier 5 — Private contractual conversations

- **Authentication:** Required.
- **Authorization:** The agent is authorized under an executed contractual agreement or purchase order.
- **Audience:** Contractually authorized parties and their authorized agents.
- **Purpose:** Perform and administer the agreed work.
- **Permitted information:** Contract- and project-specific conversations, documents, instructions, and other information necessary for contractual execution.
- **Restriction:** Access must be limited to the applicable agreement or purchase order, authorized parties, defined roles, and permitted purpose.

## Implementation requirements

1. **Default deny:** If a tier, requester identity, relationship, project scope, or authorization cannot be established, do not disclose non-public information.
2. **Separate data by tier:** Public, verified-peer, qualified-private, project-sensitive, and contract-bound information must be stored and retrieved through distinct access controls.
3. **Server-side enforcement:** Tier authorization must be evaluated on the Railway-hosted application backend and enforced in Supabase Row Level Security policies. Client-side UI gating alone is insufficient.
4. **Least privilege:** Grant only the minimum tier and scope needed for the request. Tier 4 and Tier 5 access must be project or contract specific.
5. **Purpose limitation:** A verified identity does not automatically authorize unrelated queries, projects, organizations, or contracts.
6. **Auditability:** Record authentication, tier decisions, grants, access to sensitive information, and material agent actions.
7. **Terms enforcement:** Tier 4 and Tier 5 disclosures must be governed by the relevant Build Guild terms, agreements, confidentiality obligations, and contract or purchase-order terms.
8. **Agent behavior:** Persistent agents must use only information approved for the requester's effective tier and must refuse or escalate requests that exceed that tier.

## Platform responsibility split

- **Squarespace:** Tier 0 content and the public entry points to Tier 1.
- **Railway application:** Authentication flows, tier-resolution logic, agent routing, authorization decisions, and protected application experiences.
- **Supabase:** Identity-linked records, scoped data storage, audit records, and Row Level Security enforcement.

## Tier resolution flow

1. Identify the requester and authenticate them when required.
2. Determine the requester's Build Guild verification status.
3. Determine the relationship to the organization, including competitor status when relevant.
4. Determine whether the request is organization-specific, project-specific, or contract-specific.
5. Confirm required terms, agreements, or purchase-order authorization.
6. Grant the lowest sufficient tier and limit data access to that tier's approved scope.
7. Log the decision and relevant access events.
