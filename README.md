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

## Adding a new AI-agent-facing tool

Add its endpoint and auth instructions to the `LLMS_TXT` string in
`main.py`, and consider adding a matching tile to the homepage.
