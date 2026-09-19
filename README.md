# zeroeng-site

Zero Engineering's marketing site (zeroeng.io). Recreated from the live
page's rendered HTML -- the previous source repo (`ZeroEng218/ZeroEng`) was
gone (404s on GitHub) with no other copy found, so this reproduces exactly
what was observed running in production: one page, matching styling,
`admin@zeroeng.io` contact link -- plus a new discovery surface for AI
agents:

- A visible "For AI Agents" tile linking to the public
  [zeroeng-geo-agent](https://github.com/ZeroEng218/zeroeng-geo-agent) MCP
  tool at `mcp.zeroeng.io`.
- `GET /llms.txt` -- plain-text description of the org and its live tools,
  in the format agents are starting to look for.

## Local development

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Invitation emails

Clicking **Send invite** on a project page adds the member and emails them an
invitation via [Resend](https://resend.com). Set these environment variables
(e.g. in Railway) for emails to be sent:

- `RESEND_API_KEY` -- your Resend API key (required). Without it the member is
  still added but no email is sent and the UI shows a warning.
- `FROM_EMAIL` -- verified sender, e.g. `Build Guild <no-reply@zeroeng.io>`.
  Defaults to `Build Guild <onboarding@resend.dev>` (Resend's test sender) if
  unset. Use a domain verified in your Resend account for production.
- `PUBLIC_BASE_URL` -- optional; public site URL used to build the "Accept
  invitation" link (falls back to the request host).

## Adding a new AI-agent-facing tool

Add its endpoint and auth instructions to the `LLMS_TXT` string in
`main.py`, and consider adding a matching tile to the homepage.
