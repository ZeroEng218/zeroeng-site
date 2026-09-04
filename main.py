"""
main.py

Zero Engineering's marketing site. Recreated from the live page's rendered
HTML (the previous source repo, ZeroEng218/ZeroEng, is gone -- 404s on
GitHub -- so this reproduces exactly what was observed running in
production, plus a new "for AI agents" discovery surface: a visible tile
linking to the public geo-agent MCP tool, and /llms.txt describing it in
the plain-text format agents are starting to look for.

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse

app = FastAPI(title="Zero Engineering")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zero Engineering</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&display=swap" rel="stylesheet">
    <link rel="alternate" type="text/plain" href="/llms.txt" title="For AI agents">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; background: #000; color: #fff; font-family: 'IBM Plex Mono', monospace; -webkit-font-smoothing: antialiased; }

        .stage {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            gap: 2.75rem;
            padding: 3rem 1.5rem;
        }

        /* ── Logo ── */
        .logo { display: flex; flex-direction: column; align-items: center; gap: 1.5rem; }
        .logo-mark { width: 80px; height: 80px; }
        .logo-wordmark { font-size: 1rem; font-weight: 500; letter-spacing: 0.22em; text-transform: uppercase; color: #fff; }
        .divider { width: 1px; height: 40px; background: #222; }
        .tagline { font-size: 0.85rem; font-weight: 300; letter-spacing: 0.18em; text-transform: uppercase; color: #fff; text-align: center; }
        .contact { font-size: 0.8rem; font-weight: 300; letter-spacing: 0.1em; color: #fff; text-align: center; }
        .contact a { color: #fff; text-decoration: none; border-bottom: 1px solid #555; padding-bottom: 1px; transition: border-color 0.15s; }
        .contact a:hover { border-color: #fff; }

        /* ── Services ── */
        .services-label {
            font-size: 0.6rem;
            font-weight: 400;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: #fff;
        }

        .services {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            justify-content: center;
        }

        .tile {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
            padding: 1.5rem 2rem;
            border: 1px solid #2a2a2a;
            border-top: 2px solid #fff;
            background: #080808;
            min-width: 220px;
            max-width: 320px;
            transition: border-color 0.2s, background 0.2s;
            cursor: default;
        }

        .tile:hover {
            border-color: #444;
            border-top-color: #fff;
            background: #0d0d0d;
        }

        .tile-label {
            font-size: 0.6rem;
            font-weight: 400;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #fff;
        }

        .tile-name {
            font-size: 1rem;
            font-weight: 500;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #fff;
        }

        .tile-desc {
            font-size: 0.65rem;
            font-weight: 300;
            letter-spacing: 0.05em;
            color: #fff;
            line-height: 1.7;
            margin-top: 0.25rem;
        }

        .tile-desc a { color: #fff; }

        /* ── Logo animations ── */
        .bracket-left  { animation: bracket-left-loop  9s cubic-bezier(0.4,0,0.2,1) infinite; transform-origin: 24px 60px; }
        .bracket-right { animation: bracket-right-loop 9s cubic-bezier(0.4,0,0.2,1) infinite; transform-origin: 96px 60px; }
        .ring  { stroke-dasharray: 138; animation: ring-loop 9s cubic-bezier(0.4,0,0.2,1) infinite; transform-origin: 60px 60px; }
        .dot   { animation: dot-loop 9s cubic-bezier(0.34,1.56,0.64,1) infinite; transform-origin: 60px 60px; }

        @keyframes bracket-left-loop  { 0% { transform: translateX(-10px); opacity: 0; } 15%,78% { transform: translateX(0); opacity: 1; } 92%,100% { transform: translateX(-10px); opacity: 0; } }
        @keyframes bracket-right-loop { 0% { transform: translateX(10px);  opacity: 0; } 15%,78% { transform: translateX(0); opacity: 1; } 92%,100% { transform: translateX(10px);  opacity: 0; } }
        @keyframes ring-loop { 0%,10% { stroke-dashoffset: 138; } 40%,68% { stroke-dashoffset: 0; } 88%,100% { stroke-dashoffset: 138; } }
        @keyframes dot-loop  { 0%,35% { transform: scale(0); opacity: 0; } 42% { transform: scale(1.5); opacity: 0.8; } 50%,65% { transform: scale(1); opacity: 1; } 72% { transform: scale(1.4); opacity: 0.6; } 82%,100% { transform: scale(0); opacity: 0; } }
    </style>
</head>
<body>
<div class="stage">

    <div class="logo">
        <svg class="logo-mark" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path class="bracket-left"  d="M18 25 L30 25 L30 30 L23 30 L23 90 L30 90 L30 95 L18 95 Z" fill="#444"/>
            <path class="bracket-right" d="M102 25 L90 25 L90 30 L97 30 L97 90 L90 90 L90 95 L102 95 Z" fill="#444"/>
            <rect class="ring" x="38" y="38" width="44" height="44" rx="22" ry="22" stroke="#fff" stroke-width="5" fill="none"/>
            <circle class="dot" cx="60" cy="60" r="5" fill="#fff"/>
        </svg>
        <span class="logo-wordmark">Zero Engineering</span>
    </div>

    <div class="divider"></div>

    <p class="tagline">Agentic Solutions for the Built Environment</p>

    <p class="services-label">Services</p>

    <div class="services">
        <div class="tile">
            <span class="tile-label">Offering</span>
            <span class="tile-name">MCP Server</span>
            <p class="tile-desc">Custom Model Context Protocol servers that give your AI agents secure, structured access to tools, data, and workflows.</p>
        </div>
        <div class="tile">
            <span class="tile-label">Offering</span>
            <span class="tile-name">Autodesk Dynamo</span>
            <p class="tile-desc">Parametric scripting and automation inside Revit and Civil 3D — streamlining repetitive workflows and driving data-informed design.</p>
        </div>
    </div>

    <p class="contact">contact &mdash; <a href="mailto:admin@zeroeng.io">admin@zeroeng.io</a></p>

</div>
</body>
</html>
"""

LLMS_TXT = """# Zero Engineering

> Agentic solutions for the built environment.

Zero Engineering builds AI agent tooling for companies that serve the
built environment (architecture, engineering, construction). Some of that
tooling is published as public MCP servers any agent can call directly --
no relationship with us required beyond a free, instant API key.

## Live tools

### Geo Lookup (MCP)

- Endpoint: https://mcp.zeroeng.io/mcp (streamable-http)
- Auth: POST https://mcp.zeroeng.io/register with {"name": "...", "email": "..."}
  to get a free API key instantly. Send it back as
  `Authorization: Bearer <api_key>` on requests to /mcp.
- Tool: get_state_for_coordinates(latitude, longitude) -> the U.S. state and
  county a coordinate falls within, backed by the FCC/Census Bureau's
  authoritative boundary data (not model guesswork).
- More location-based operations (jurisdiction lookup, permitting rules,
  code requirements) are planned on the same endpoint.

## Services

- MCP Server -- custom Model Context Protocol servers giving AI agents
  secure, structured access to tools, data, and workflows.
- Autodesk Dynamo -- parametric scripting and automation inside Revit and
  Civil 3D.

## Contact

admin@zeroeng.io
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return PAGE


@app.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt():
    return LLMS_TXT


@app.get("/health")
async def health():
    return {"status": "ok"}
