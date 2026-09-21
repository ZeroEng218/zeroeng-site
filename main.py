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

import datetime
import hashlib
import json
import logging
import math
import os
import secrets as secrets_mod
from typing import Any, Optional

from jose import jwt

from fastapi import Cookie, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)

app = FastAPI(title="Zero Engineering")

# CORS -- allow any origin so AI agents (e.g. Abacus) can connect to /mcp.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Supabase client (lazy, cached) ────────────────────────────────────────
# Credentials come from the environment (set as Railway variables in prod):
#   SUPABASE_URL, SUPABASE_ANON_KEY
_supabase_client = None


def get_supabase():
    """Return a cached Supabase client, or None if not configured/available."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
    except Exception:
        return None
    return _supabase_client

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zero Engineering &mdash; AI-Native Geospatial Intelligence</title>
    <meta name="description" content="An open MCP server connecting AI agents to authoritative environmental and infrastructure data: soils, flood zones, wetlands, and street maps.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="alternate" type="text/plain" href="/llms.txt" title="For AI agents">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #0a0a0a;
            --bg-soft: #0f0f10;
            --panel: #121214;
            --border: #232327;
            --border-hi: #34343a;
            --text: #f2f2f4;
            --muted: #9a9aa2;
            --faint: #6a6a72;
            --cyan: #00d4ff;
            --green: #00ff88;
        }
        html { scroll-behavior: smooth; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', system-ui, sans-serif;
            -webkit-font-smoothing: antialiased;
            line-height: 1.6;
            background-image:
                radial-gradient(circle at 15% 10%, rgba(0,212,255,0.06), transparent 40%),
                radial-gradient(circle at 85% 0%, rgba(0,255,136,0.04), transparent 35%),
                linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 44px 44px, 44px 44px;
        }
        code, .mono { font-family: 'IBM Plex Mono', monospace; }
        a { color: inherit; text-decoration: none; }
        .wrap { max-width: 1120px; margin: 0 auto; padding: 0 1.5rem; }
        .accent { color: var(--cyan); }

        /* Nav */
        nav {
            position: sticky; top: 0; z-index: 50;
            backdrop-filter: blur(12px);
            background: rgba(10,10,10,0.72);
            border-bottom: 1px solid var(--border);
        }
        .nav-inner { display: flex; align-items: center; justify-content: space-between; height: 64px; }
        .brand { display: flex; align-items: center; gap: 0.7rem; }
        .brand svg { width: 30px; height: 30px; }
        .brand-name { font-weight: 600; letter-spacing: 0.16em; font-size: 0.82rem; text-transform: uppercase; }
        .nav-links { display: flex; align-items: center; gap: 1.75rem; }
        .nav-links a { font-size: 0.85rem; color: var(--muted); transition: color 0.15s; }
        .nav-links a:hover { color: var(--text); }
        .status { display: flex; align-items: center; gap: 0.5rem; font-size: 0.72rem; color: var(--muted); }
        .status .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 0 rgba(0,255,136,0.6); animation: pulse 2s infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0,255,136,0.5);} 70% { box-shadow: 0 0 0 8px rgba(0,255,136,0);} 100% { box-shadow: 0 0 0 0 rgba(0,255,136,0);} }
        @media (max-width: 780px){ .nav-links a:not(.nav-cta){ display:none; } }

        /* Hero */
        .hero { padding: 5.5rem 0 3.5rem; text-align: center; }
        .eyebrow { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:0.7rem; letter-spacing:0.24em; text-transform:uppercase; color: var(--cyan); border:1px solid var(--border-hi); border-radius:999px; padding:0.35rem 0.9rem; margin-bottom:1.6rem; }
        .hero h1 { font-size: clamp(2.1rem, 5.5vw, 3.6rem); font-weight: 700; letter-spacing: -0.02em; line-height: 1.08; background: linear-gradient(180deg, #fff, #b9c6cc); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .hero p.sub { max-width: 720px; margin: 1.4rem auto 0; color: var(--muted); font-size: clamp(0.98rem, 2vw, 1.14rem); font-weight: 300; }

        /* Connection box */
        .conn { max-width: 760px; margin: 2.6rem auto 0; background: linear-gradient(180deg, var(--panel), var(--bg-soft)); border: 1px solid var(--border-hi); border-radius: 14px; padding: 1.5rem; text-align: left; box-shadow: 0 20px 60px -30px rgba(0,212,255,0.35); }
        .conn-label { font-size: 0.68rem; letter-spacing: 0.2em; text-transform: uppercase; color: var(--faint); margin-bottom: 0.7rem; display:flex; align-items:center; gap:0.4rem;}
        .conn-row { display: flex; gap: 0.6rem; align-items: stretch; flex-wrap: wrap; }
        .conn-url { flex: 1 1 320px; display:flex; align-items:center; font-family: 'IBM Plex Mono', monospace; font-size: 0.98rem; color: var(--text); background: #060606; border: 1px solid var(--border); border-radius: 9px; padding: 0.75rem 0.95rem; overflow-x:auto; }
        .btn { border: 1px solid var(--border-hi); background: #17171a; color: var(--text); font-family: inherit; font-size: 0.82rem; font-weight: 500; padding: 0.75rem 1.05rem; border-radius: 9px; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
        .btn:hover { border-color: var(--cyan); color: var(--cyan); }
        .btn.primary { background: var(--cyan); color: #04121a; border-color: var(--cyan); }
        .btn.primary:hover { background: #33ddff; color: #04121a; }
        .conn-meta { margin-top: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem 1.4rem; font-size: 0.76rem; color: var(--muted); font-family:'IBM Plex Mono',monospace; }
        .conn-meta b { color: var(--text); font-weight: 500; }
        .conn-note { margin-top: 0.85rem; font-size: 0.78rem; color: var(--faint); }

        /* Sections */
        section { padding: 4rem 0; }
        .sec-head { text-align: center; margin-bottom: 2.6rem; }
        .sec-head .kicker { font-family:'IBM Plex Mono',monospace; font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase; color: var(--cyan); }
        .sec-head h2 { font-size: clamp(1.5rem, 3.5vw, 2.1rem); font-weight: 600; letter-spacing: -0.01em; margin-top: 0.5rem; }

        /* Tools grid */
        .tools { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
        .tool { background: var(--panel); border: 1px solid var(--border); border-radius: 13px; padding: 1.4rem; transition: border-color 0.2s, transform 0.2s; }
        .tool:hover { border-color: var(--border-hi); transform: translateY(-3px); }
        .tool-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.9rem; }
        .tool-ico { font-size: 1.5rem; }
        .badge { font-family:'IBM Plex Mono',monospace; font-size: 0.62rem; letter-spacing: 0.06em; text-transform: uppercase; padding: 0.28rem 0.6rem; border-radius: 999px; border: 1px solid var(--border-hi); color: var(--muted); }
        .badge.geo { color: var(--green); border-color: rgba(0,255,136,0.35); }
        .tool h3 { font-family: 'IBM Plex Mono', monospace; font-size: 1rem; font-weight: 500; color: var(--cyan); margin-bottom: 0.5rem; }
        .tool p { font-size: 0.86rem; color: var(--muted); font-weight: 300; margin-bottom: 0.9rem; }
        .params { font-family:'IBM Plex Mono',monospace; font-size: 0.72rem; color: var(--faint); background: #060606; border: 1px solid var(--border); border-radius: 7px; padding: 0.55rem 0.7rem; margin-bottom: 0.9rem; overflow-x:auto; }
        .params span { color: var(--text); }
        .src { font-size: 0.72rem; color: var(--faint); }
        .src b { color: var(--muted); font-weight: 500; }

        /* Connect columns */
        .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin-bottom: 1.6rem; }
        .col { background: var(--panel); border: 1px solid var(--border); border-radius: 13px; padding: 1.4rem; }
        .col h4 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.9rem; display:flex; align-items:center; gap:0.5rem; }
        .col ol { list-style: none; counter-reset: step; }
        .col ol li { counter-increment: step; position: relative; padding-left: 2rem; margin-bottom: 0.6rem; font-size: 0.84rem; color: var(--muted); font-weight: 300; }
        .col ol li::before { content: counter(step); position: absolute; left: 0; top: 0; width: 1.35rem; height: 1.35rem; background: #17171a; border: 1px solid var(--border-hi); color: var(--cyan); border-radius: 50%; font-family:'IBM Plex Mono',monospace; font-size: 0.68rem; display:flex; align-items:center; justify-content:center; }
        .col code { color: var(--text); font-size: 0.8rem; word-break: break-all; }
        .codeblock { position: relative; background: #060606; border: 1px solid var(--border); border-radius: 11px; padding: 1.1rem 1.2rem; overflow-x: auto; }
        .codeblock pre { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; color: #cdd6db; line-height: 1.7; }
        .codeblock .k { color: var(--cyan); }
        .codeblock .s { color: var(--green); }
        .codeblock .copy { position: absolute; top: 0.7rem; right: 0.7rem; padding: 0.4rem 0.7rem; font-size: 0.72rem; }

        /* Use cases */
        .cases { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
        .case { background: linear-gradient(180deg, var(--panel), var(--bg-soft)); border: 1px solid var(--border); border-radius: 13px; padding: 1.6rem; }
        .case .ci { font-size: 1.7rem; margin-bottom: 0.8rem; }
        .case h4 { font-size: 1.02rem; font-weight: 600; margin-bottom: 0.5rem; }
        .case p { font-size: 0.86rem; color: var(--muted); font-weight: 300; }

        /* About */
        .about { max-width: 760px; margin: 0 auto; text-align: center; }
        .about p { color: var(--muted); font-size: 1.02rem; font-weight: 300; }
        .about .stack { margin-top: 1.4rem; font-family:'IBM Plex Mono',monospace; font-size: 0.76rem; color: var(--faint); letter-spacing: 0.05em; }
        .about .ghbtn { display:inline-block; margin-top: 1.6rem; }

        /* Footer */
        footer { border-top: 1px solid var(--border); padding: 2.5rem 0; }
        .foot-inner { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; }
        .foot-inner p { font-size: 0.76rem; color: var(--faint); max-width: 560px; }
        .foot-links { display: flex; gap: 1.3rem; font-size: 0.8rem; }
        .foot-links a { color: var(--muted); } .foot-links a:hover { color: var(--cyan); }

        /* Build Guild Banner */
        .bg-banner {
            background: linear-gradient(135deg, #1a1200 0%, #201800 60%, #0f0d00 100%);
            border: 1px solid rgba(240,165,0,0.35);
            border-radius: 16px;
            padding: 1.8rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
            flex-wrap: wrap;
            box-shadow: 0 0 40px -10px rgba(240,165,0,0.2);
            margin: 2rem auto 0;
            max-width: 760px;
        }
        .bg-banner-left { display: flex; align-items: center; gap: 1rem; }
        .bg-icon { font-size: 2.2rem; }
        .bg-banner-text {}
        .bg-banner-eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; letter-spacing: 0.2em; text-transform: uppercase; color: #f0a500; margin-bottom: 0.25rem; }
        .bg-banner-title { font-size: 1.1rem; font-weight: 700; color: #fff; letter-spacing: -0.01em; }
        .bg-banner-sub { font-size: 0.82rem; color: #b8a060; margin-top: 0.2rem; }
        .btn-guild { background: #f0a500; color: #0f0a00; border: none; font-family: inherit; font-size: 0.88rem; font-weight: 700; padding: 0.75rem 1.4rem; border-radius: 10px; cursor: pointer; transition: all 0.15s; white-space: nowrap; text-decoration: none; display: inline-block; }
        .btn-guild:hover { background: #ffc233; color: #0f0a00; transform: translateY(-1px); }

        /* toast */
        .toast { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%) translateY(20px); background: var(--green); color: #04120a; font-weight: 600; font-size: 0.85rem; padding: 0.7rem 1.3rem; border-radius: 9px; opacity: 0; pointer-events: none; transition: all 0.25s; z-index: 100; }
        .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

        /* logo anim */
        .ring2 { stroke-dasharray: 138; animation: ringloop 9s cubic-bezier(0.4,0,0.2,1) infinite; transform-origin: 60px 60px; }
        .dot2 { animation: dotloop 9s cubic-bezier(0.34,1.56,0.64,1) infinite; transform-origin: 60px 60px; }
        @keyframes ringloop { 0%,10% { stroke-dashoffset: 138; } 40%,68% { stroke-dashoffset: 0; } 88%,100% { stroke-dashoffset: 138; } }
        @keyframes dotloop { 0%,35% { transform: scale(0); opacity: 0; } 50%,65% { transform: scale(1); opacity: 1; } 82%,100% { transform: scale(0); opacity: 0; } }
    </style>
</head>
<body>

<nav>
  <div class="wrap nav-inner">
    <a class="brand" href="#top">
      <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect class="ring2" x="38" y="38" width="44" height="44" rx="22" ry="22" stroke="#00d4ff" stroke-width="6" fill="none"/>
        <circle class="dot2" cx="60" cy="60" r="6" fill="#fff"/>
      </svg>
      <span class="brand-name">Zero Engineering</span>
    </a>
    <div class="nav-links">
      <a href="#tools">Tools</a>
      <a href="#connect">Connect</a>
      <a href="#cases">Use Cases</a>
      <a href="#about">About</a>
      <a href="/build-guild" style="color:#f0a500;font-weight:600;">Build Guild</a>
      <a href="https://github.com/ZeroEng218/zeroeng-site" target="_blank" rel="noopener">GitHub</a>
      <span class="status"><span class="dot"></span>MCP Server Online</span>
    </div>
  </div>
</nav>

<a id="top"></a>
<header class="hero">
  <div class="wrap">
    <span class="eyebrow">Model Context Protocol &bull; Live</span>
    <h1>AI-Native Geospatial Intelligence</h1>
    <p class="sub">An open MCP server connecting AI agents to authoritative environmental and infrastructure data &mdash; soils, flood zones, wetlands, and street maps &mdash; ready for Civil 3D workflows.</p>

    <div class="conn">
      <div class="conn-label">&#128268; MCP Server URL</div>
      <div class="conn-row">
        <div class="conn-url" id="mcpUrl">https://www.zeroeng.io/mcp</div>
        <button class="btn primary" onclick="copyText('https://www.zeroeng.io/mcp', this)">Copy URL</button>
        <a class="btn" href="/health" target="_blank" rel="noopener">Test Connection</a>
      </div>
      <div class="conn-meta">
        <span>Transport: <b>Streamable HTTP</b></span>
        <span>Protocol: <b>JSON-RPC 2.0</b></span>
        <span>Auth: <b>None required</b></span>
      </div>
      <p class="conn-note">Compatible with Abacus AI, Claude Desktop, Cursor, Windsurf, and any MCP client.</p>
    </div>

    <a href="/build-guild" class="bg-banner" style="text-decoration:none;">
      <div class="bg-banner-left">
        <div class="bg-icon">&#127963;</div>
        <div class="bg-banner-text">
          <div class="bg-banner-eyebrow">Agentic Marketplace &bull; Now Open</div>
          <div class="bg-banner-title">The Build Guild</div>
          <div class="bg-banner-sub">Register your firm and connect AI agents across the built environment &mdash; free to join.</div>
        </div>
      </div>
      <span class="btn-guild">Join the Guild &rarr;</span>
    </a>

  </div>
</header>

<section id="tools">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">Capabilities</span>
      <h2>5 Available Tools</h2>
    </div>
    <div class="tools">

      <div class="tool">
        <div class="tool-top"><span class="tool-ico">&#127793;</span><span class="badge geo">Returns GeoJSON</span></div>
        <h3>soil_lookup</h3>
        <p>Soil series, drainage class, texture, and hydric rating with polygon boundaries for any US coordinate.</p>
        <div class="params">{ <span>lat</span>, <span>lon</span>, radius_meters? }</div>
        <div class="src"><b>Source:</b> USDA SSURGO</div>
      </div>

      <div class="tool">
        <div class="tool-top"><span class="tool-ico">&#127754;</span><span class="badge geo">Returns GeoJSON</span></div>
        <h3>fema_flood_lookup</h3>
        <p>FEMA flood zone designation (AE, X, VE&hellip;), base flood elevation, and SFHA status with boundaries.</p>
        <div class="params">{ <span>lat</span>, <span>lon</span> }</div>
        <div class="src"><b>Source:</b> FEMA NFHL</div>
      </div>

      <div class="tool">
        <div class="tool-top"><span class="tool-ico">&#127807;</span><span class="badge geo">Returns GeoJSON</span></div>
        <h3>wetland_lookup</h3>
        <p>NWI Cowardin classification, acreage, and Section 404 regulatory flags with polygon boundaries.</p>
        <div class="params">{ <span>lat</span>, <span>lon</span> }</div>
        <div class="src"><b>Source:</b> USFWS NWI</div>
      </div>

      <div class="tool">
        <div class="tool-top"><span class="tool-ico">&#128506;</span><span class="badge geo">Returns GeoJSON</span></div>
        <h3>osm_lookup</h3>
        <p>Roads, buildings, utilities, waterways, and land use features. Filterable by category.</p>
        <div class="params">{ <span>lat</span>, <span>lon</span>, radius_meters?, categories? }</div>
        <div class="src"><b>Source:</b> OpenStreetMap</div>
      </div>

      <div class="tool">
        <div class="tool-top"><span class="tool-ico">&#127963;</span><span class="badge">Returns Text</span></div>
        <h3>state_capital_lookup</h3>
        <p>Returns the capital city for any US state. Demo tool showcasing Supabase integration.</p>
        <div class="params">{ <span>state</span> }</div>
        <div class="src"><b>Source:</b> Zero Engineering DB</div>
      </div>

    </div>
  </div>
</section>

<section id="connect" style="background:var(--bg-soft); border-top:1px solid var(--border); border-bottom:1px solid var(--border);">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">Integration</span>
      <h2>Connect in 60 Seconds</h2>
    </div>
    <div class="cols">
      <div class="col">
        <h4>&#129302; Abacus AI</h4>
        <ol>
          <li>Open MCP Server Configurations</li>
          <li>Click Add MCP Server</li>
          <li>Name: <code>ZeroEng</code></li>
          <li>URL: <code>https://www.zeroeng.io/mcp</code></li>
          <li>Transport: Streamable HTTP</li>
          <li>Save &amp; ask your agent</li>
        </ol>
      </div>
      <div class="col">
        <h4>&#128421; Claude Desktop</h4>
        <ol>
          <li>Edit <code>claude_desktop_config.json</code></li>
          <li>Add an <code>mcpServers</code> entry with the URL</li>
          <li>Restart Claude Desktop</li>
        </ol>
      </div>
      <div class="col">
        <h4>&#9889; Cursor / Windsurf</h4>
        <ol>
          <li>Open MCP settings</li>
          <li>Add server with the URL</li>
          <li>Transport: HTTP</li>
        </ol>
      </div>
    </div>

    <div class="codeblock">
      <button class="btn copy" onclick="copyConfig(this)">Copy</button>
      <pre id="cfg"><span class="k">{</span>
  <span class="k">"mcpServers"</span>: {
    <span class="k">"zeroeng"</span>: {
      <span class="k">"url"</span>: <span class="s">"https://www.zeroeng.io/mcp"</span>,
      <span class="k">"transport"</span>: <span class="s">"streamable-http"</span>
    }
  }
<span class="k">}</span></pre>
    </div>
  </div>
</section>

<section id="cases">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">Applications</span>
      <h2>Built for the Built Environment</h2>
    </div>
    <div class="cases">
      <div class="case">
        <div class="ci">&#127959;</div>
        <h4>Civil Engineering</h4>
        <p>Automated site assessments piped directly into Civil 3D and Autodesk Dynamo as labeled polylines.</p>
      </div>
      <div class="case">
        <div class="ci">&#127807;</div>
        <h4>Environmental Review</h4>
        <p>Instant soil, flood, and wetland data for any project location &mdash; no manual portal downloads.</p>
      </div>
      <div class="case">
        <div class="ci">&#129302;</div>
        <h4>Agentic Workflows</h4>
        <p>Connect AI agents to authoritative GIS data without building or managing a single API integration.</p>
      </div>
    </div>
  </div>
</section>

<section id="about" style="background:var(--bg-soft); border-top:1px solid var(--border);">
  <div class="wrap about">
    <div class="sec-head"><span class="kicker">Mission</span><h2>About Zero Engineering</h2></div>
    <p>Zero Engineering is an R&amp;D initiative exploring agentic workflows for the built environment &mdash; finding real value in AI-native infrastructure tools that benefit the AEC industry.</p>
    <div class="stack">Built with FastAPI &bull; Railway &bull; Supabase</div>
    <a class="btn ghbtn" href="https://github.com/ZeroEng218/zeroeng-site" target="_blank" rel="noopener">View on GitHub &rarr;</a>
  </div>
</section>

<footer>
  <div class="wrap foot-inner">
    <p>&copy; 2025 Zero Engineering. Data provided by USDA, FEMA, USFWS, and OpenStreetMap contributors.</p>
    <div class="foot-links">
      <a href="https://github.com/ZeroEng218/zeroeng-site" target="_blank" rel="noopener">GitHub</a>
      <a href="/llms.txt">llms.txt</a>
      <a href="/health">Health Check</a>
    </div>
  </div>
</footer>

<div class="toast" id="toast">Copied!</div>

<script>
  function showToast(msg){
    var t = document.getElementById('toast');
    t.textContent = msg || 'Copied!';
    t.classList.add('show');
    clearTimeout(window.__tt);
    window.__tt = setTimeout(function(){ t.classList.remove('show'); }, 1600);
  }
  function copyText(text, btn){
    navigator.clipboard.writeText(text).then(function(){
      var old = btn.textContent; btn.textContent = 'Copied!';
      showToast('URL copied to clipboard');
      setTimeout(function(){ btn.textContent = old; }, 1400);
    }).catch(function(){ showToast('Copy failed'); });
  }
  function copyConfig(btn){
    var cfg = document.getElementById('cfg').innerText;
    navigator.clipboard.writeText(cfg).then(function(){
      var old = btn.textContent; btn.textContent = 'Copied!';
      showToast('Config copied to clipboard');
      setTimeout(function(){ btn.textContent = old; }, 1400);
    }).catch(function(){ showToast('Copy failed'); });
  }
</script>

</body>
</html>
"""

LLMS_TXT = """# Zero Engineering

> Agentic solutions for the built environment.

Zero Engineering builds AI agent tooling for companies that serve the
built environment (architecture, engineering, construction). Some of that
tooling is published as public MCP servers any agent can call directly --
no relationship with us required.

## Live tools (MCP)

- Endpoint: /mcp (streamable HTTP, JSON-RPC 2.0)
- No API key required. Standard MCP handshake: `initialize`, then
  `tools/list`, then `tools/call`.

### state_capital_lookup

- Args: state (string) -- the name of a U.S. state.
- Returns: the capital city of that state, from an authoritative table
  (not model guesswork).

### soil_lookup

- Args: lat (number), lon (number), radius_meters (number, optional,
  default 500). Coordinates are WGS84 decimal degrees.
- Returns: USDA SSURGO soil map units at that point -- map unit name,
  dominant component, drainage class, hydric rating, taxonomic order and
  class, surface texture -- plus GeoJSON polygon boundaries for each map
  unit, backed by the USDA Soil Data Access API (authoritative survey data).
- Intended for CAD/GIS agents: e.g. Civil 3D / Dynamo can call this with a
  lat/lon and draw the returned soil polygons directly in a drawing.
- Coverage is the U.S. and its territories; offshore or international
  points return no soil units.

### fema_flood_lookup

- Args: lat (number), lon (number). Coordinates are WGS84 decimal degrees.
- Returns: FEMA National Flood Hazard Layer (NFHL) flood zone(s) at that
  point -- flood zone designation (e.g. AE, X, VE, AO), zone subtype,
  human-readable risk level and description, Special Flood Hazard Area
  (SFHA) flag, base flood elevation, FIRM panel and source citation --
  plus GeoJSON polygon boundaries for each flood zone, backed by FEMA's
  public NFHL ArcGIS service (authoritative flood-map data).
- Intended for CAD/GIS agents: e.g. Civil 3D / Dynamo can call this with a
  lat/lon and draw the returned flood-zone polygons directly in a drawing.
- Coverage is mapped U.S. communities; unmapped, offshore, or international
  points return no flood zones.

### wetland_lookup

- Args: lat (number), lon (number). Coordinates are WGS84 decimal degrees.
- Returns: USFWS National Wetlands Inventory (NWI) wetland feature(s) at that
  point -- Cowardin attribute code (e.g. PEM1C, PFO1A), wetland type, system
  (Palustrine/Estuarine/Riverine/Lacustrine/Marine), class (Emergent,
  Forested, Scrub-Shrub, ...), water regime, special modifiers, acreage, a
  plain-language description, and a Clean Water Act Section 404 / Section 10
  regulatory note -- plus GeoJSON polygon boundaries for each wetland, backed
  by the USFWS NWI ArcGIS service (authoritative wetland-mapping data).
- Intended for CAD/GIS agents: e.g. Civil 3D / Dynamo can call this with a
  lat/lon and draw the returned wetland polygons directly in a drawing.
- Coverage is mapped U.S. areas; unmapped, offshore, or international points
  return no wetlands (field verification still recommended).

### osm_lookup

- Args: lat (number), lon (number), radius_meters (number, optional,
  default 200, max 1000), categories (array of strings, optional). Category
  options: roads, buildings, waterways, utilities, landuse, railways,
  amenities. Omit categories to query all. Coordinates are WGS84 decimal
  degrees.
- Returns: OpenStreetMap features near the point via the Overpass API --
  each with OSM id/type, category, feature type, name, raw tags, and GeoJSON
  geometry (Point for nodes, LineString/Polygon for ways) -- plus a
  per-category feature_summary count. Capped at 200 features per call.
- Intended for CAD/GIS agents: e.g. Civil 3D / Dynamo can call this with a
  lat/lon and draw roads, utilities, buildings, and waterways as separate
  labeled layers directly in a drawing.
- Data (c) OpenStreetMap contributors, licensed ODbL
  (https://www.openstreetmap.org/copyright).
- Worldwide coverage; density varies by area.

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
    # The Build Guild is now the site's landing page. The former
    # "AI-Native Geospatial Intelligence" page (PAGE) has been deprecated and
    # is no longer surfaced; legacy geospatial URLs redirect here (see below).
    return BUILD_GUILD_PAGE


# Legacy redirects for the deprecated geospatial landing page. Any old links
# pointing at the former home page now land on the Build Guild.
@app.get("/geospatial")
@app.get("/ai-native-geospatial-intelligence")
async def geospatial_deprecated():
    return RedirectResponse("/", status_code=301)


@app.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt():
    return LLMS_TXT


@app.get("/health")
async def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────
# MCP (Model Context Protocol) server -- Streamable HTTP transport.
#
# A single POST /mcp endpoint speaking JSON-RPC 2.0, per the MCP spec. It
# handles `initialize`, `tools/list`, and `tools/call`. One tool is exposed:
# `state_capital_lookup`, which reads the `states` table in Supabase.
#
# Example (list tools):
#   curl -s https://<host>/mcp -H 'content-type: application/json' \
#     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# Example (call the tool):
#   curl -s https://<host>/mcp -H 'content-type: application/json' \
#     -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
#          "params":{"name":"state_capital_lookup","arguments":{"state":"Texas"}}}'
# ─────────────────────────────────────────────────────────────────────────

MCP_PROTOCOL_VERSION = "2024-11-05"

SERVER_INFO = {"name": "zeroeng-mcp", "version": "1.0.0"}

TOOLS = [
    {
        "name": "build_guild_register",
        "description": (
            "Register an organization with The Build Guild agentic marketplace. "
            "The Build Guild is a project-scoped marketplace for the built environment — "
            "connecting AI agents acting on behalf of architects, engineers, contractors, "
            "vendors, and owners. "
            "Registration is free (Tier: free, $0). "
            "On success, returns a project_credential JWT valid for 365 days. "
            "Present this credential as: Authorization: Bearer <project_credential> "
            "on all authenticated Build Guild requests. "
            "IMPORTANT: Before calling this tool, confirm the registration details "
            "(org_name, role, contact_name, contact_email) with your human operator. "
            "This confirmation is the recommended human-in-the-loop checkpoint."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "org_name": {
                    "type": "string",
                    "description": "The name of the organization to register (e.g. 'Acme Engineering')",
                },
                "role": {
                    "type": "string",
                    "enum": ["Architect", "Engineer", "Contractor", "Vendor", "Owner"],
                    "description": "The organization's primary role in the AEC industry",
                },
                "contact_name": {
                    "type": "string",
                    "description": "Full name of the primary contact person",
                },
                "contact_email": {
                    "type": "string",
                    "description": "Email address of the primary contact person",
                },
                "a2a_endpoint": {
                    "type": "string",
                    "description": (
                        "Optional. Your organization's own A2A (Agent-to-Agent) "
                        "endpoint URL. If provided, your agent becomes directly "
                        "discoverable and callable by other verified Guild members "
                        "via the member directory."
                    ),
                },
            },
            "required": ["org_name", "role", "contact_name", "contact_email"],
        },
    },
    {
        "name": "find_agents",
        "description": (
            "Search the Build Guild member directory for registered AEC "
            "organizations. Optionally filter by role or restrict to members "
            "with A2A endpoints for direct agent-to-agent communication. "
            "Requires a valid project_credential JWT from build_guild_register."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_credential": {
                    "type": "string",
                    "description": "Your Build Guild project_credential JWT (from build_guild_register). Required.",
                },
                "role": {
                    "type": "string",
                    "enum": ["Architect", "Engineer", "Contractor", "Vendor", "Owner"],
                    "description": "Filter by AEC role (optional — omit to return all roles)",
                },
                "a2a_only": {
                    "type": "boolean",
                    "description": "If true, only return members that have registered an A2A endpoint",
                },
                "search": {
                    "type": "string",
                    "description": "Optional text search across org_name (case-insensitive)",
                },
            },
            "required": ["project_credential"],
        },
    },
]


def _rpc_result(msg_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _rpc_error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _tool_text(text: str, is_error: bool = False) -> dict:
    """Build an MCP tools/call result payload."""
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def state_capital_lookup(state: str) -> dict:
    """Query Supabase `states` table (case-insensitive) for the capital."""
    if not state or not str(state).strip():
        return _tool_text("Error: 'state' argument is required.", is_error=True)

    client = get_supabase()
    if client is None:
        return _tool_text(
            "Error: Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_ANON_KEY environment variables.",
            is_error=True,
        )

    query_state = str(state).strip()
    try:
        # ilike gives case-insensitive exact-name matching.
        resp = (
            client.table("states")
            .select("state, capital")
            .ilike("state", query_state)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:  # network / query failure
        return _tool_text(f"Error querying Supabase: {exc}", is_error=True)

    if not rows:
        return _tool_text(
            f"No US state named '{query_state}' was found.", is_error=True
        )

    row = rows[0]
    return _tool_text(
        f"The capital of {row['state']} is {row['capital']}."
    )


def _tool_json(payload: dict, is_error: bool = False) -> dict:
    """Build an MCP tools/call result whose text content is a JSON string.

    Agents (and Civil 3D / Dynamo consumers) can json.loads the text to get
    the structured soil result, including GeoJSON geometry.
    """
    return {
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "isError": is_error,
    }


# USDA Soil Data Access (SDA) endpoint -- public, no auth required.
SDA_TABULAR_URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
WEB_SOIL_SURVEY_URL = "https://websoilsurvey.sc.egov.usda.gov/"


def _sda_query(sql: str, timeout: int = 30):
    """POST an SQL query to the USDA SDA REST API and return parsed rows.

    With FORMAT=JSON+COLUMNNAME, SDA returns {"Table": [[col, col, ...], ...]}
    where the FIRST row is the column headers. Returns a list of dicts. Raises
    on transport failure; returns [] when SDA reports no data.
    """
    import requests

    resp = requests.post(
        SDA_TABULAR_URL,
        data={"query": sql, "FORMAT": "JSON+COLUMNNAME"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout,
    )
    resp.raise_for_status()
    # SDA returns an empty body (not JSON) when there are no matching rows.
    text = (resp.text or "").strip()
    if not text:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    table = data.get("Table") if isinstance(data, dict) else None
    if not table or len(table) < 2:
        return []
    headers = table[0]
    return [dict(zip(headers, row)) for row in table[1:]]


def _wkts_to_geojson(wkt_list):
    """Combine one or more WKT polygon strings into a single GeoJSON geometry.

    A soil map unit (mukey) can be made up of several disjoint polygons within
    the search area. We keep each polygon distinct (no dissolve) so a CAD/GIS
    consumer can draw every boundary: one Polygon becomes a GeoJSON Polygon,
    several become a MultiPolygon.
    """
    if not wkt_list:
        return None
    try:
        from shapely import wkt as shapely_wkt
        from shapely.geometry import MultiPolygon, mapping

        polys = []
        for w in wkt_list:
            if not w:
                continue
            try:
                geom = shapely_wkt.loads(w)
            except Exception:
                continue
            if geom.geom_type == "Polygon":
                polys.append(geom)
            elif geom.geom_type == "MultiPolygon":
                polys.extend(list(geom.geoms))
        if not polys:
            return None
        if len(polys) == 1:
            return mapping(polys[0])
        return mapping(MultiPolygon(polys))
    except Exception:
        return None


def soil_lookup(lat, lon, radius_meters=500) -> dict:
    """Look up USDA SSURGO soil map units + boundaries for a coordinate.

    Two-step SDA query: (1) tabular soil/component attributes, (2) polygon
    geometry as WKT -> converted to GeoJSON. Results are keyed by mukey.
    """
    # ── Validate inputs ──────────────────────────────────────────────
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return _tool_json(
            {
                "error": "Both 'lat' and 'lon' are required and must be numbers.",
            },
            is_error=True,
        )

    if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
        return _tool_json(
            {
                "error": (
                    "Coordinates out of range. lat must be in [-90, 90] and "
                    "lon in [-180, 180]."
                ),
                "location": {"lat": lat_f, "lon": lon_f},
            },
            is_error=True,
        )

    try:
        radius_f = float(radius_meters) if radius_meters is not None else 500.0
    except (TypeError, ValueError):
        radius_f = 500.0

    # Build a small WGS84 bounding box of the requested radius around the
    # point. The box scopes BOTH the attribute and geometry queries, so
    # radius_meters is honored and the returned geometry stays local (rather
    # than every polygon of a map unit across the entire survey area).
    dlat = radius_f / 111320.0
    dlon = radius_f / (111320.0 * max(math.cos(math.radians(lat_f)), 1e-6))
    minx, maxx = lon_f - dlon, lon_f + dlon
    miny, maxy = lat_f - dlat, lat_f + dlat
    box_wkt = (
        f"polygon(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, "
        f"{minx} {maxy}, {minx} {miny}))"
    )

    # ── Step 1: tabular attributes for map units within the radius ───
    attr_sql = f"""SELECT mu.mukey, mu.muname, c.compname, c.majcompflag, c.drainagecl, c.hydricrating,
       c.taxorder, c.taxclname, soi.texture
FROM mapunit mu
INNER JOIN component c ON c.mukey = mu.mukey AND c.majcompflag = 'Yes'
LEFT JOIN chorizon ch ON ch.cokey = c.cokey AND ch.hzdept_r = 0
LEFT JOIN chtexturegrp soi ON soi.chkey = ch.chkey AND soi.rvindicator = 'Yes'
WHERE mu.mukey IN (
  SELECT mukey FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{box_wkt}')
)"""

    # ── Step 2: polygon geometry (WKT) for polygons within the radius ─
    geom_sql = f"""SELECT mp.mukey, mp.mupolygongeo.STAsText() as wkt_geometry
FROM mupolygon mp
WHERE mp.mupolygonkey IN (
  SELECT mupolygonkey FROM SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84('{box_wkt}')
)"""

    try:
        attr_rows = _sda_query(attr_sql)
    except Exception as exc:
        return _tool_json(
            {
                "error": (
                    "USDA Soil Data Access API is unreachable. Please retry "
                    "later or check the location at the USDA Web Soil Survey."
                ),
                "detail": str(exc),
                "location": {"lat": lat_f, "lon": lon_f},
                "usda_web_soil_survey": WEB_SOIL_SURVEY_URL,
            },
            is_error=True,
        )

    if not attr_rows:
        return _tool_json(
            {
                "location": {"lat": lat_f, "lon": lon_f},
                "soil_units": [],
                "message": (
                    "No USDA SSURGO soil data is available for this point. "
                    "SSURGO covers the U.S. and its territories; offshore, "
                    "international, or unmapped areas return no results."
                ),
                "source": "USDA SSURGO via Soil Data Access API",
                "usda_web_soil_survey": WEB_SOIL_SURVEY_URL,
            }
        )

    # Fetch geometry; a geometry failure should not lose the tabular data.
    # Collect all polygon WKTs per mukey (a unit may span several polygons).
    wkts_by_mukey = {}
    try:
        for g in _sda_query(geom_sql):
            mukey = str(g.get("mukey", "")).strip()
            wkt = g.get("wkt_geometry")
            if mukey and wkt:
                wkts_by_mukey.setdefault(mukey, []).append(wkt)
    except Exception:
        wkts_by_mukey = {}

    geom_by_mukey = {
        mukey: _wkts_to_geojson(wkts) for mukey, wkts in wkts_by_mukey.items()
    }

    # ── Assemble one entry per unique mukey ──────────────────────────
    # Each map unit can list several major components; prefer the row with
    # the most populated attributes so we surface real soil data (e.g. "Fox,
    # Well drained") rather than a sparse "Urban land" row with null fields.
    def _completeness(row):
        return sum(
            1
            for k in ("drainagecl", "hydricrating", "taxorder", "taxclname", "texture")
            if row.get(k) not in (None, "")
        )

    best_row = {}
    for r in attr_rows:
        mukey = str(r.get("mukey", "")).strip()
        if not mukey:
            continue
        if mukey not in best_row or _completeness(r) > _completeness(best_row[mukey]):
            best_row[mukey] = r

    soil_units = []
    for mukey, r in best_row.items():
        soil_units.append(
            {
                "mukey": mukey,
                "muname": r.get("muname"),
                "component_name": r.get("compname"),
                "drainage_class": r.get("drainagecl"),
                "hydric_rating": r.get("hydricrating"),
                "tax_order": r.get("taxorder"),
                "tax_class": r.get("taxclname"),
                "surface_texture": r.get("texture"),
                "geometry": geom_by_mukey.get(mukey),
            }
        )

    return _tool_json(
        {
            "location": {"lat": lat_f, "lon": lon_f},
            "radius_meters": radius_f,
            "soil_units": soil_units,
            "source": "USDA SSURGO via Soil Data Access API",
            "usda_web_soil_survey": WEB_SOIL_SURVEY_URL,
        }
    )


# ─────────────────────────────────────────────────────────────────────────
# FEMA National Flood Hazard Layer (NFHL) -- public ArcGIS REST service,
# no API key required. Layer 28 is the Flood Hazard Zones layer.
# ─────────────────────────────────────────────────────────────────────────
FEMA_NFHL_URL = (
    "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/"
    "MapServer/28/query"
)
FEMA_MSC_URL = "https://msc.fema.gov/portal/home"

# ArcGIS "no data" sentinel used for numeric fields like BFE / depth / velocity.
_FEMA_NODATA = -9999.0

FLOOD_ZONE_DESCRIPTIONS = {
    "A": "High risk - Special Flood Hazard Area (SFHA). 1% annual chance flood.",
    "AE": "High risk - SFHA with Base Flood Elevations. 1% annual chance flood.",
    "AH": "High risk - SFHA with shallow flooding (ponding). 1% annual chance flood.",
    "AO": "High risk - SFHA with sheet flow flooding. 1% annual chance flood.",
    "AR": "High risk - SFHA with temporary increased risk due to levee failure.",
    "A99": "High risk - SFHA protected by Federal flood control system under construction.",
    "V": "Very high risk - Coastal SFHA with wave action. 1% annual chance flood.",
    "VE": "Very high risk - Coastal SFHA with wave action and BFE. 1% annual chance flood.",
    "B": "Moderate risk - Area between 1% and 0.2% annual chance flood.",
    "C": "Minimal risk - Area of minimal flood hazard.",
    "X": "Minimal to moderate risk. Zone X (shaded) = 0.2% annual chance. Zone X (unshaded) = minimal hazard.",
    "D": "Undetermined risk - Possible flood hazards but not analyzed.",
}

# Short, human-readable risk level per zone code.
_FLOOD_RISK_LEVELS = {
    "A": "High risk",
    "AE": "High risk",
    "AH": "High risk",
    "AO": "High risk",
    "AR": "High risk",
    "A99": "High risk",
    "V": "Very high risk",
    "VE": "Very high risk",
    "B": "Moderate risk",
    "C": "Minimal risk",
    "X": "Minimal to moderate risk",
    "D": "Undetermined risk",
}


def _flood_risk_level(zone):
    """Return a short risk-level label for a FEMA flood zone code."""
    if not zone:
        return "Unknown"
    return _FLOOD_RISK_LEVELS.get(str(zone).strip().upper(), "Unknown")


def _flood_zone_description(zone):
    """Return the human-readable description for a FEMA flood zone code."""
    if not zone:
        return "Unknown flood zone."
    return FLOOD_ZONE_DESCRIPTIONS.get(
        str(zone).strip().upper(),
        f"Flood zone {zone} - see FEMA for details.",
    )


def _fema_num(value):
    """Return a numeric field, or None if it is missing / the -9999 sentinel."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f == _FEMA_NODATA:
        return None
    return f


def _esri_rings_to_geojson(rings):
    """Convert an ESRI polygon's `rings` to a GeoJSON geometry.

    ESRI already returns coordinates as [x, y] = [lon, lat] (outSR=4326), which
    is the order GeoJSON expects. Per the NFHL feature model a flood-zone
    polygon's first ring is the exterior boundary and any remaining rings are
    interior holes, so we emit a single GeoJSON Polygon (exterior + holes) that
    a CAD/GIS consumer can draw directly.
    """
    if not rings:
        return None

    def _close(ring):
        # GeoJSON linear rings must be explicitly closed.
        if ring and ring[0] != ring[-1]:
            return ring + [ring[0]]
        return ring

    coords = [_close([list(pt) for pt in ring]) for ring in rings if ring]
    coords = [r for r in coords if len(r) >= 4]
    if not coords:
        return None
    return {"type": "Polygon", "coordinates": coords}


def _fema_query(lat, lon, timeout=30):
    """Query the FEMA NFHL layer 28 for flood zones intersecting a point.

    Returns the parsed ArcGIS JSON dict. Retries a few times because the FEMA
    endpoint intermittently resets TLS connections.
    """
    import time as _time

    import requests

    params = {
        "geometry": json.dumps(
            {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}
        ),
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        # Request all fields; NFHL layer 28 lacks some FIRM-panel columns, and
        # asking for a non-existent field makes ArcGIS reject the whole query.
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json",
    }
    last_exc = None
    for attempt in range(4):
        try:
            resp = requests.get(FEMA_NFHL_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # transport / TLS reset / JSON error
            last_exc = exc
            _time.sleep(1.5 * (attempt + 1))
    raise last_exc if last_exc else RuntimeError("FEMA NFHL request failed")


def fema_flood_lookup(lat, lon) -> dict:
    """Look up FEMA NFHL flood zone(s) + boundaries for a coordinate."""
    # ── Validate inputs ──────────────────────────────────────────────
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return _tool_json(
            {"error": "Both 'lat' and 'lon' are required and must be numbers."},
            is_error=True,
        )

    if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
        return _tool_json(
            {
                "error": (
                    "Coordinates out of range. lat must be in [-90, 90] and "
                    "lon in [-180, 180]."
                ),
                "location": {"lat": lat_f, "lon": lon_f},
            },
            is_error=True,
        )

    # ── Query FEMA NFHL ──────────────────────────────────────────────
    try:
        data = _fema_query(lat_f, lon_f)
    except Exception as exc:
        return _tool_json(
            {
                "error": (
                    "FEMA National Flood Hazard Layer service is unreachable. "
                    "Please retry later or check the location at the FEMA Flood "
                    "Map Service Center."
                ),
                "detail": str(exc),
                "location": {"lat": lat_f, "lon": lon_f},
                "fema_flood_map_service_center": FEMA_MSC_URL,
            },
            is_error=True,
        )

    if isinstance(data, dict) and data.get("error"):
        return _tool_json(
            {
                "error": "FEMA NFHL query failed.",
                "detail": data.get("error"),
                "location": {"lat": lat_f, "lon": lon_f},
                "fema_flood_map_service_center": FEMA_MSC_URL,
            },
            is_error=True,
        )

    features = (data or {}).get("features") or []
    if not features:
        return _tool_json(
            {
                "location": {"lat": lat_f, "lon": lon_f},
                "flood_zones": [],
                "summary": (
                    "No FEMA flood zone data found at this location. It may fall "
                    "outside NFHL coverage (unmapped community, offshore, or "
                    "international)."
                ),
                "source": "FEMA National Flood Hazard Layer (NFHL)",
                "fema_flood_map_service_center": FEMA_MSC_URL,
            }
        )

    # ── Assemble flood zones ─────────────────────────────────────────
    flood_zones = []
    any_sfha = False
    zone_codes = []
    for feat in features:
        attrs = feat.get("attributes") or {}
        geom = feat.get("geometry") or {}
        zone = attrs.get("FLD_ZONE")
        sfha = str(attrs.get("SFHA_TF") or "").strip().upper() == "T"
        if sfha:
            any_sfha = True
        if zone:
            zone_codes.append(str(zone).strip().upper())
        flood_zones.append(
            {
                "flood_zone": zone,
                "zone_subtype": attrs.get("ZONE_SUBTY"),
                "risk_level": _flood_risk_level(zone),
                "risk_description": _flood_zone_description(zone),
                "special_flood_hazard_area": sfha,
                "base_flood_elevation": _fema_num(attrs.get("STATIC_BFE")),
                "firm_panel": attrs.get("FIRM_PAN"),
                "source_citation": attrs.get("SOURCE_CIT"),
                "geometry": _esri_rings_to_geojson(geom.get("rings")),
            }
        )

    n = len(flood_zones)
    zone_list = ", ".join(sorted(set(c for c in zone_codes if c))) or "unclassified"
    if any_sfha:
        summary = (
            f"{n} flood zone{'s' if n != 1 else ''} found ({zone_list}). "
            "HIGH RISK - Special Flood Hazard Area (SFHA) present."
        )
    else:
        summary = (
            f"{n} flood zone{'s' if n != 1 else ''} found ({zone_list}). "
            "No Special Flood Hazard Area (SFHA) at this location."
        )

    return _tool_json(
        {
            "location": {"lat": lat_f, "lon": lon_f},
            "flood_zones": flood_zones,
            "summary": summary,
            "source": "FEMA National Flood Hazard Layer (NFHL)",
            "fema_flood_map_service_center": FEMA_MSC_URL,
        }
    )


# ─────────────────────────────────────────────────────────────────────────
# USFWS National Wetlands Inventory (NWI) -- public ArcGIS REST service,
# no API key required. Layer 0 is the Wetlands polygon layer. Coordinates
# (Cowardin classification) are parsed from the ATTRIBUTE code.
# ─────────────────────────────────────────────────────────────────────────
NWI_WETLANDS_URL = (
    "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/"
    "Wetlands/MapServer/0/query"
)
NWI_MAPPER_URL = (
    "https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper"
)

# Cowardin system codes (first char of the ATTRIBUTE code).
WETLAND_SYSTEMS = {
    "M": "Marine",
    "E": "Estuarine",
    "R": "Riverine",
    "L": "Lacustrine",
    "P": "Palustrine",
    "U": "Upland (non-wetland)",
}

# Cowardin class codes (two-letter class following the system/subsystem).
WETLAND_CLASSES = {
    "AB": "Aquatic Bed",
    "EM": "Emergent",
    "FO": "Forested",
    "ML": "Mudflat",
    "OW": "Open Water",
    "RF": "Reef",
    "RB": "Rock Bottom",
    "SB": "Streambed",
    "SC": "Scrub-Shrub",
    "SS": "Scrub-Shrub",
    "UB": "Unconsolidated Bottom",
    "US": "Unconsolidated Shore",
}

# Cowardin water-regime codes (single letter following the class/subclass).
WATER_REGIMES = {
    "A": "Temporarily Flooded",
    "B": "Seasonally Saturated",
    "C": "Seasonally Flooded",
    "D": "Continuously Saturated",
    "E": "Seasonally Flooded / Saturated",
    "F": "Semi-permanently Flooded",
    "G": "Intermittently Exposed",
    "H": "Permanently Flooded",
    "J": "Intermittently Flooded",
    "K": "Artificially Flooded",
    "L": "Subtidal",
    "M": "Irregularly Exposed",
    "N": "Regularly Flooded",
    "P": "Irregularly Flooded",
    "R": "Tidal Freshwater",
    "S": "Temporarily Flooded/Saturated",
    "T": "Seasonally Flooded/Saturated",
    "V": "Permanently Flooded/Tidal",
    "W": "Seasonally Flooded/Tidal",
    "X": "Regularly Flooded/Tidal",
    "Y": "Permanently Flooded/Tidal",
    "Z": "Intermittently Flooded/Tidal",
}

# Special modifiers appended to a Cowardin code (as "/x" or a trailing letter).
WETLAND_SPECIAL_MODIFIERS = {
    "d": "Diked/Impounded",
    "r": "Partly Drained",
    "x": "Excavated",
    "f": "Farmed",
}

# Short definitions for the common classes, used to enrich the description.
_WETLAND_CLASS_DEFS = {
    "EM": "Characterized by erect, rooted, herbaceous hydrophytes.",
    "FO": "Characterized by woody vegetation at least 6 m (20 ft) tall.",
    "SS": "Characterized by woody vegetation less than 6 m (20 ft) tall.",
    "SC": "Characterized by woody vegetation less than 6 m (20 ft) tall.",
    "AB": "Characterized by plants growing on or below the water surface.",
    "OW": "Open water with less than 30% areal cover of vegetation.",
    "UB": "Bottom with less than 25% cover of stones/boulders and no vegetation.",
    "US": "Shore with less than 75% cover of vegetation or bedrock.",
}


def _nwi_attr(attrs: dict, field: str):
    """Read a field from an NWI feature, tolerating table-qualified names.

    The NWI layer joins the Wetlands polygons to a codes table, so ArcGIS
    returns keys like `Wetlands.ATTRIBUTE` and `NWI_Wetland_Codes.SYSTEM`.
    Fall back to the plain field name too.
    """
    if not isinstance(attrs, dict):
        return None
    if field in attrs:
        return attrs[field]
    for prefix in ("Wetlands.", "NWI_Wetland_Codes."):
        if prefix + field in attrs:
            return attrs[prefix + field]
    # Last resort: match on the unqualified suffix.
    for k, v in attrs.items():
        if k.split(".")[-1] == field:
            return v
    return None


def _parse_cowardin(code):
    """Parse an NWI Cowardin ATTRIBUTE code into its components.

    Returns a dict with system_code, system, class_code, class, water_regime,
    and special_modifiers. Handles optional subsystem digit (M/E/R/L),
    subclass digit(s), trailing modifier letters, and slash modifiers.
    """
    out = {
        "system_code": None,
        "system": None,
        "class_code": None,
        "class": None,
        "water_regime": None,
        "special_modifiers": [],
    }
    if not code:
        return out

    raw = str(code).strip()
    parts = raw.split("/")
    base = parts[0]
    slash_segments = parts[1:]

    mods = []
    for seg in slash_segments:
        if not seg:
            continue
        m = WETLAND_SPECIAL_MODIFIERS.get(seg[0].lower())
        mods.append(m if m else f"Modifier '{seg}'")

    i, n = 0, len(base)

    # System (first char).
    if i < n and base[i].isalpha():
        sys_char = base[i].upper()
        out["system_code"] = sys_char
        out["system"] = WETLAND_SYSTEMS.get(sys_char)
        i += 1
    else:
        sys_char = ""

    # Optional subsystem digit for Marine/Estuarine/Riverine/Lacustrine.
    if sys_char in ("M", "E", "R", "L") and i < n and base[i].isdigit():
        i += 1

    # Class: up to two alpha characters.
    if i < n and base[i].isalpha():
        cls = base[i : i + 2]
        if len(cls) == 2 and cls[1].isalpha():
            i += 2
        else:
            cls = base[i]
            i += 1
        out["class_code"] = cls.upper()
        out["class"] = WETLAND_CLASSES.get(cls.upper())

    # Subclass digit(s).
    while i < n and base[i].isdigit():
        i += 1

    # Water regime: single alpha character.
    if i < n and base[i].isalpha():
        wr = base[i].upper()
        out["water_regime"] = WATER_REGIMES.get(wr)
        i += 1

    # Trailing letters are special modifiers.
    while i < n:
        m = WETLAND_SPECIAL_MODIFIERS.get(base[i].lower())
        if m:
            mods.append(m)
        i += 1

    out["special_modifiers"] = mods
    return out


def _wetland_description(parsed, wetland_type):
    """Build a human-readable wetland description from parsed components."""
    system = parsed.get("system") or "Wetland"
    wclass = parsed.get("class") or ""
    regime = parsed.get("water_regime")

    lead = f"{system} {wclass}".strip()
    desc = f"{lead} wetland" if wclass else f"{lead}"
    if regime:
        desc += f" - {regime.lower()}"
    desc += "."

    class_def = _WETLAND_CLASS_DEFS.get(parsed.get("class_code") or "")
    if class_def:
        desc += " " + class_def
    if parsed.get("special_modifiers"):
        desc += " Modifiers: " + ", ".join(parsed["special_modifiers"]) + "."
    return desc


def _wetland_regulatory_note(parsed, wetland_type):
    """Build a regulatory jurisdiction note for a wetland feature."""
    system_code = parsed.get("system_code")
    notes = []
    if system_code in ("P", "E", "R", "L"):
        notes.append(
            "Likely subject to Section 404 CWA jurisdiction. Consult with USACE."
        )
    if wetland_type and "freshwater" in str(wetland_type).lower():
        notes.append(
            "Freshwater wetland - U.S. Army Corps Section 404 permit may apply."
        )
    if system_code in ("E", "M"):
        notes.append(
            "Tidal/coastal - Section 10 Rivers & Harbors Act may also apply."
        )
    if not notes:
        notes.append("Consult with USACE for a jurisdictional determination.")
    return " ".join(notes)


def _nwi_query(lat, lon, timeout=30):
    """Query the USFWS NWI wetlands layer for polygons intersecting a point.

    Returns the parsed ArcGIS JSON dict. Uses outFields=* because the layer's
    join rejects unqualified field lists; retries on transient TLS resets.
    """
    import time as _time

    import requests

    params = {
        "geometry": json.dumps(
            {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}
        ),
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json",
    }
    last_exc = None
    for attempt in range(4):
        try:
            resp = requests.get(NWI_WETLANDS_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # transport / TLS reset / JSON error
            last_exc = exc
            _time.sleep(1.5 * (attempt + 1))
    raise last_exc if last_exc else RuntimeError("NWI request failed")


def wetland_lookup(lat, lon) -> dict:
    """Look up USFWS NWI wetland classification(s) + boundaries for a point."""
    # ── Validate inputs ──────────────────────────────────────────────
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return _tool_json(
            {"error": "Both 'lat' and 'lon' are required and must be numbers."},
            is_error=True,
        )

    if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
        return _tool_json(
            {
                "error": (
                    "Coordinates out of range. lat must be in [-90, 90] and "
                    "lon in [-180, 180]."
                ),
                "location": {"lat": lat_f, "lon": lon_f},
            },
            is_error=True,
        )

    # ── Query USFWS NWI ──────────────────────────────────────────────
    try:
        data = _nwi_query(lat_f, lon_f)
    except Exception as exc:
        return _tool_json(
            {
                "error": (
                    "USFWS National Wetlands Inventory service is unreachable. "
                    "Please retry later or check the location at the NWI "
                    "Wetlands Mapper."
                ),
                "detail": str(exc),
                "location": {"lat": lat_f, "lon": lon_f},
                "nwi_mapper": NWI_MAPPER_URL,
            },
            is_error=True,
        )

    if isinstance(data, dict) and data.get("error"):
        return _tool_json(
            {
                "error": "USFWS NWI query failed.",
                "detail": data.get("error"),
                "location": {"lat": lat_f, "lon": lon_f},
                "nwi_mapper": NWI_MAPPER_URL,
            },
            is_error=True,
        )

    features = (data or {}).get("features") or []
    if not features:
        return _tool_json(
            {
                "location": {"lat": lat_f, "lon": lon_f},
                "wetlands": [],
                "summary": (
                    "No NWI wetland features mapped at this location. Field "
                    "verification recommended."
                ),
                "no_wetlands_found": True,
                "source": "USFWS National Wetlands Inventory (NWI)",
                "nwi_mapper": NWI_MAPPER_URL,
            }
        )

    # ── Assemble wetland features ────────────────────────────────────
    wetlands = []
    for feat in features:
        attrs = feat.get("attributes") or {}
        geom = feat.get("geometry") or {}
        code = _nwi_attr(attrs, "ATTRIBUTE")
        wetland_type = _nwi_attr(attrs, "WETLAND_TYPE")
        acres_raw = _nwi_attr(attrs, "ACRES")
        try:
            acres = round(float(acres_raw), 2) if acres_raw is not None else None
        except (TypeError, ValueError):
            acres = None

        parsed = _parse_cowardin(code)
        wetlands.append(
            {
                "attribute_code": code,
                "wetland_type": wetland_type,
                "system": parsed.get("system"),
                "class": parsed.get("class"),
                "water_regime": parsed.get("water_regime"),
                "special_modifiers": parsed.get("special_modifiers", []),
                "acres": acres,
                "description": _wetland_description(parsed, wetland_type),
                "regulatory_note": _wetland_regulatory_note(parsed, wetland_type),
                "geometry": _esri_rings_to_geojson(geom.get("rings")),
            }
        )

    n = len(wetlands)
    summary = (
        f"{n} wetland feature{'s' if n != 1 else ''} found. "
        "Wetlands present - Section 404 review likely required."
    )

    return _tool_json(
        {
            "location": {"lat": lat_f, "lon": lon_f},
            "wetlands": wetlands,
            "summary": summary,
            "no_wetlands_found": False,
            "source": "USFWS National Wetlands Inventory (NWI)",
            "nwi_mapper": NWI_MAPPER_URL,
        }
    )


# ─────────────────────────────────────────────────────────────────────────
# OpenStreetMap (OSM) via the Overpass API -- free, public, no API key.
# A single bounding-box query pulls infrastructure features (roads,
# buildings, waterways, utilities, land use, railways, amenities) and their
# geometry, which we convert to GeoJSON for CAD/GIS consumers.
# ─────────────────────────────────────────────────────────────────────────
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
OSM_USER_AGENT = "ZeroEng-MCP/1.0 (admin@zeroeng.io)"

# Cap the number of features returned so responses stay manageable.
OSM_MAX_FEATURES = 200
# Radius bounds (meters).
OSM_DEFAULT_RADIUS = 200.0
OSM_MAX_RADIUS = 1000.0

# Overpass QL statement fragments per category. `{bbox}` is substituted with
# the "south,west,north,east" bounding box.
OSM_CATEGORY_QUERIES = {
    "roads": [
        'way["highway"]({bbox});',
    ],
    "buildings": [
        'way["building"]({bbox});',
        'relation["building"]({bbox});',
    ],
    "waterways": [
        'way["waterway"]({bbox});',
        'node["waterway"]({bbox});',
        'relation["waterway"]({bbox});',
        'way["natural"~"water|wetland|coastline"]({bbox});',
    ],
    "utilities": [
        'way["power"]({bbox});',
        'node["power"]({bbox});',
        'way["man_made"~"pipeline|utility_pole|tower"]({bbox});',
        'node["man_made"~"pipeline|utility_pole|tower"]({bbox});',
        'node["utility"]({bbox});',
    ],
    "landuse": [
        'way["landuse"]({bbox});',
        'relation["landuse"]({bbox});',
    ],
    "railways": [
        'way["railway"]({bbox});',
        'node["railway"]({bbox});',
    ],
    "amenities": [
        'node["amenity"]({bbox});',
        'way["amenity"]({bbox});',
    ],
}

OSM_ALL_CATEGORIES = list(OSM_CATEGORY_QUERIES.keys())


def classify_osm_feature(tags):
    """Classify an OSM element by its tags -> (category, feature_type)."""
    tags = tags or {}
    if "highway" in tags:
        hw = tags["highway"]
        road_types = {
            "motorway": "Interstate/Motorway",
            "trunk": "Primary Arterial",
            "primary": "Primary Road",
            "secondary": "Secondary Road",
            "tertiary": "Tertiary Road",
            "residential": "Residential Road",
            "service": "Service Road",
            "footway": "Footway/Path",
            "cycleway": "Cycle Path",
            "path": "Path/Trail",
            "unclassified": "Unclassified Road",
        }
        return "roads", road_types.get(hw, f"Road ({hw})")
    if "building" in tags:
        return "buildings", f"Building ({tags.get('building', 'yes')})"
    if "waterway" in tags:
        return "waterways", f"Waterway ({tags.get('waterway', 'unknown')})"
    if "natural" in tags and tags["natural"] in ("water", "wetland", "coastline"):
        return "waterways", f"Natural water ({tags['natural']})"
    if "power" in tags:
        return "utilities", f"Power ({tags.get('power', 'unknown')})"
    if "man_made" in tags:
        return "utilities", f"Infrastructure ({tags.get('man_made', 'unknown')})"
    if "utility" in tags:
        return "utilities", f"Utility ({tags.get('utility', 'unknown')})"
    if "landuse" in tags:
        return "landuse", f"Land use ({tags.get('landuse', 'unknown')})"
    if "railway" in tags:
        return "railways", f"Railway ({tags.get('railway', 'unknown')})"
    if "amenity" in tags:
        return "amenities", f"Amenity ({tags.get('amenity', 'unknown')})"
    return "other", "Unknown feature"


def _osm_way_geometry(way, node_lookup):
    """Reconstruct a way's GeoJSON geometry from the node coordinate lookup.

    A way whose first and last node coincide AND which is tagged as an area
    (building / landuse / natural / amenity area) becomes a GeoJSON Polygon;
    otherwise it is a LineString.
    """
    node_ids = way.get("nodes") or []
    coords = []
    for nid in node_ids:
        pt = node_lookup.get(nid)
        if pt is not None:
            coords.append([pt[0], pt[1]])  # [lon, lat]
    if len(coords) < 2:
        return None

    tags = way.get("tags") or {}
    is_closed = len(coords) >= 4 and coords[0] == coords[-1]
    area_tag = (
        "building" in tags
        or "landuse" in tags
        or tags.get("natural") in ("water", "wetland")
        or (tags.get("area") == "yes")
    )
    if is_closed and area_tag:
        return {"type": "Polygon", "coordinates": [coords]}
    return {"type": "LineString", "coordinates": coords}


def _build_overpass_query(bbox, categories):
    """Assemble the full Overpass QL query for the requested categories."""
    stmts = []
    for cat in categories:
        for frag in OSM_CATEGORY_QUERIES.get(cat, []):
            stmts.append(frag.format(bbox=bbox))
    body = "\n".join(stmts)
    return (
        "[out:json][timeout:25];\n"
        "(\n" + body + "\n);\n"
        "out body; >; out skel qt;"
    )


def _overpass_request(query, timeout=40):
    """POST an Overpass query, trying the primary then fallback endpoint."""
    import requests

    last_exc = None
    for url in OVERPASS_ENDPOINTS:
        try:
            resp = requests.post(
                url,
                data={"data": query},
                headers={"User-Agent": OSM_USER_AGENT},
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # transport / HTTP / JSON error
            last_exc = exc
            continue
    raise last_exc if last_exc else RuntimeError("Overpass request failed")


def osm_lookup(lat, lon, radius_meters=200, categories=None) -> dict:
    """Query OSM (Overpass) for infrastructure features near a coordinate."""
    # ── Validate inputs ──────────────────────────────────────────────
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return _tool_json(
            {"error": "Both 'lat' and 'lon' are required and must be numbers."},
            is_error=True,
        )

    if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lon_f <= 180.0):
        return _tool_json(
            {
                "error": (
                    "Coordinates out of range. lat must be in [-90, 90] and "
                    "lon in [-180, 180]."
                ),
                "location": {"lat": lat_f, "lon": lon_f},
            },
            is_error=True,
        )

    # Radius: default 200 m, capped at 1000 m.
    try:
        radius_f = float(radius_meters) if radius_meters is not None else OSM_DEFAULT_RADIUS
    except (TypeError, ValueError):
        radius_f = OSM_DEFAULT_RADIUS
    if radius_f <= 0:
        radius_f = OSM_DEFAULT_RADIUS
    radius_f = min(radius_f, OSM_MAX_RADIUS)

    # Categories: default to all; validate against the known set.
    if categories is None:
        req_categories = list(OSM_ALL_CATEGORIES)
    else:
        if isinstance(categories, str):
            categories = [categories]
        req_categories = [
            str(c).strip().lower()
            for c in categories
            if str(c).strip().lower() in OSM_CATEGORY_QUERIES
        ]
        if not req_categories:
            req_categories = list(OSM_ALL_CATEGORIES)

    # ── Bounding box from radius ─────────────────────────────────────
    dlat = radius_f / 111320.0
    dlon = radius_f / (111320.0 * max(math.cos(math.radians(lat_f)), 1e-6))
    # Overpass bbox order is south,west,north,east.
    bbox = f"{lat_f - dlat},{lon_f - dlon},{lat_f + dlat},{lon_f + dlon}"

    query = _build_overpass_query(bbox, req_categories)

    # ── Query Overpass ───────────────────────────────────────────────
    try:
        data = _overpass_request(query)
    except Exception as exc:
        return _tool_json(
            {
                "error": (
                    "OpenStreetMap Overpass API is unreachable. Please retry "
                    "later."
                ),
                "detail": str(exc),
                "location": {"lat": lat_f, "lon": lon_f},
                "source": "OpenStreetMap contributors",
                "osm_license": f"ODbL - {OSM_COPYRIGHT_URL}",
            },
            is_error=True,
        )

    elements = (data or {}).get("elements") or []

    # Build node lookup {id: [lon, lat]} for way/relation geometry.
    node_lookup = {}
    for el in elements:
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            node_lookup[el["id"]] = [el["lon"], el["lat"]]

    # ── Parse elements into features ─────────────────────────────────
    features = []
    summary = {c: 0 for c in OSM_ALL_CATEGORIES}
    summary["total"] = 0

    for el in elements:
        if len(features) >= OSM_MAX_FEATURES:
            break
        etype = el.get("type")
        tags = el.get("tags") or {}
        # Skip untagged skeleton nodes used only for geometry.
        if not tags:
            continue

        category, feature_type = classify_osm_feature(tags)
        # Only surface features in the requested categories.
        if category not in req_categories:
            continue

        if etype == "node":
            if "lat" in el and "lon" in el:
                geometry = {"type": "Point", "coordinates": [el["lon"], el["lat"]]}
            else:
                geometry = None
        elif etype == "way":
            geometry = _osm_way_geometry(el, node_lookup)
        else:  # relation -- geometry reconstruction is out of scope; keep metadata
            geometry = None

        features.append(
            {
                "osm_id": el.get("id"),
                "osm_type": etype,
                "category": category,
                "feature_type": feature_type,
                "name": tags.get("name"),
                "tags": tags,
                "geometry": geometry,
            }
        )
        if category in summary:
            summary[category] += 1
        summary["total"] += 1

    return _tool_json(
        {
            "location": {"lat": lat_f, "lon": lon_f},
            "radius_meters": radius_f,
            "categories": req_categories,
            "feature_summary": summary,
            "features": features,
            "source": "OpenStreetMap contributors",
            "osm_license": f"ODbL - {OSM_COPYRIGHT_URL}",
        }
    )


def _handle_rpc(message: dict) -> Optional[dict]:
    """Handle a single JSON-RPC message. Returns None for notifications."""
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    # Notifications (no id) -- e.g. notifications/initialized. No response.
    if msg_id is None and method and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return _rpc_result(
            msg_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method == "ping":
        return _rpc_result(msg_id, {})

    if method == "tools/list":
        return _rpc_result(msg_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "build_guild_register":
            return _rpc_result(
                msg_id,
                build_guild_register_tool(
                    arguments.get("org_name"),
                    arguments.get("role"),
                    arguments.get("contact_name"),
                    arguments.get("contact_email"),
                    arguments.get("a2a_endpoint"),
                ),
            )
        if name == "find_agents":
            return _rpc_result(
                msg_id,
                find_agents_tool(
                    arguments.get("project_credential"),
                    arguments.get("role"),
                    arguments.get("a2a_only"),
                    arguments.get("search"),
                ),
            )
        return _rpc_error(msg_id, -32602, f"Unknown tool: {name}")

    return _rpc_error(msg_id, -32601, f"Method not found: {method}")


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            _rpc_error(None, -32700, "Parse error: invalid JSON"), status_code=400
        )

    # Support both a single message and a batch.
    if isinstance(payload, list):
        responses = [r for r in (_handle_rpc(m) for m in payload) if r is not None]
        if not responses:
            return JSONResponse(content=None, status_code=202)
        return JSONResponse(content=responses)

    if not isinstance(payload, dict):
        return JSONResponse(
            _rpc_error(None, -32600, "Invalid Request"), status_code=400
        )

    response = _handle_rpc(payload)
    if response is None:
        # Notification -- acknowledge with no body.
        return JSONResponse(content=None, status_code=202)
    return JSONResponse(content=response)



# ---------------------------------------------------------------------------
# Agent discovery endpoints & The Build Guild sub-page
# ---------------------------------------------------------------------------

MCP_DISCOVERY = {
    "schema_version": "1.0",
    "name": "Zero Engineering MCP",
    "description": "An open MCP server providing authoritative geospatial and environmental data for the built environment — soils, flood zones, wetlands, and street maps.",
    "mcp_endpoint": "https://www.zeroeng.io/mcp",
    "transport": "streamable-http",
    "protocol": "json-rpc-2.0",
    "authentication": {
        "required": False,
        "type": "none"
    },
    "tools": [
        {
            "name": "soil_lookup",
            "description": "Returns USDA SSURGO soil series, drainage class, texture, hydric rating, and GeoJSON boundaries for any US coordinate.",
            "source": "USDA SSURGO",
            "inputs": ["lat", "lon", "radius_meters (optional)"],
            "returns": "GeoJSON FeatureCollection"
        },
        {
            "name": "fema_flood_lookup",
            "description": "Returns FEMA flood zone designation (AE, X, VE, etc.), base flood elevation, SFHA status, and GeoJSON boundaries.",
            "source": "FEMA NFHL",
            "inputs": ["lat", "lon"],
            "returns": "GeoJSON FeatureCollection"
        },
        {
            "name": "wetland_lookup",
            "description": "Returns USFWS NWI wetland classification (Cowardin system), acreage, Section 404 regulatory flags, and GeoJSON boundaries.",
            "source": "USFWS NWI",
            "inputs": ["lat", "lon"],
            "returns": "GeoJSON FeatureCollection"
        },
        {
            "name": "osm_lookup",
            "description": "Returns roads, buildings, utilities, waterways, and land use features with GeoJSON geometries from OpenStreetMap.",
            "source": "OpenStreetMap",
            "inputs": ["lat", "lon", "radius_meters (optional)", "categories (optional)"],
            "returns": "GeoJSON FeatureCollection"
        },
        {
            "name": "state_capital_lookup",
            "description": "Returns the capital city for any US state.",
            "source": "Zero Engineering DB",
            "inputs": ["state"],
            "returns": "string"
        },
        {
            "name": "build_guild_register",
            "description": "Register an organization with The Build Guild agentic marketplace (free tier, $0). Returns a project_credential JWT valid for 365 days. Completable entirely within an LLM session. Optionally accepts an a2a_endpoint.",
            "source": "The Build Guild",
            "inputs": ["org_name", "role", "contact_name", "contact_email", "a2a_endpoint (optional)"],
            "returns": "project_credential JWT"
        },
        {
            "name": "find_agents",
            "description": "Search the Build Guild member directory for registered AEC organizations. Filter by role or restrict to members with A2A endpoints. Requires a valid project_credential JWT.",
            "source": "The Build Guild",
            "inputs": ["project_credential", "role (optional)", "a2a_only (optional)", "search (optional)"],
            "returns": "list of members"
        }
    ],
    "related": {
        "build_guild": "https://www.zeroeng.io/build-guild",
        "agent_manifest": "https://www.zeroeng.io/.well-known/agent-manifest",
        "a2a_agent_card": "https://www.zeroeng.io/.well-known/agent.json",
        "a2a_endpoint": "https://www.zeroeng.io/a2a",
        "llms_txt": "https://www.zeroeng.io/llms.txt"
    }
}


AGENT_MANIFEST = {
    "schema_version": "1.0",
    "manifest_type": "agentic-marketplace",
    "identity": {
        "name": "The Build Guild",
        "operator": "Zero Engineering",
        "home_url": "https://www.zeroeng.io/build-guild",
        "description": "A secure, AHJ-sanctioned agent-to-agent marketplace for the built environment. AI agents representing licensed architects, engineers, contractors, vendors, and owners connect, discover, and communicate directly — scoped by role and operating under the authority of the jurisdictions that govern their activities.",
        "purpose": "To provide the trust infrastructure for safe, secure agent-to-agent communication across the architecture, engineering, and construction industry — sanctioned by the authorities having jurisdiction over those activities in each state."
    },
    "authentication": {
        "status": "unauthenticated",
        "message": "You have arrived without credentials. Registration is agent-callable — your agent can complete signup within your LLM session. See how_to_register for the endpoint and required fields.",
        "required_for": "All marketplace transactions, project affiliation, and agent-to-agent messaging require a verified Build Guild account.",
        "how_to_register": {
            "method": "mcp-tool",
            "mcp_tool": "build_guild_register",
            "mcp_endpoint": "https://www.zeroeng.io/mcp",
            "description": "Registration is fully completable within your LLM session — no browser or external HTTP client required. Recommended path: connect to the MCP server and call the build_guild_register tool. A REST fallback (POST /build-guild/register with a JSON body) is also available.",
            "endpoint": "POST https://www.zeroeng.io/build-guild/register",
            "content_type": "application/json",
            "request_body": {
                "org_name": "Your organization name (string, required)",
                "role": "One of: Architect, Engineer, Contractor, Vendor, Owner (required)",
                "contact_name": "Your full name (string, required)",
                "contact_email": "Your email address (string, required)"
            },
            "tiers": {
                "free": {
                    "price": "$0",
                    "includes": [
                        "Verified org profile in the Build Guild marketplace",
                        "Access to all public MCP geospatial tools",
                        "Receive RFPs addressed to your organization",
                        "project_credential JWT valid for 365 days"
                    ]
                }
            },
            "on_success": "You will receive a project_credential (JWT). Present it as: Authorization: Bearer <project_credential> on all authenticated Build Guild requests.",
            "human_in_the_loop": "Before calling this endpoint, confirm the registration details with your human operator. This is the recommended human approval checkpoint.",
            "contact": "guild@zeroeng.io"
        }
    },
    "capabilities": {
        "unauthenticated": [
            "Read this agent manifest",
            "Discover available MCP tools at /.well-known/mcp.json",
            "Access the Zero Engineering public MCP server at /mcp",
            "View the Build Guild landing page at /build-guild"
        ],
        "authenticated": [
            "Create and manage a project profile",
            "Affiliate your agent with one or more projects",
            "Post project needs (RFIs, RFPs, submittals) to the marketplace",
            "Receive bids and proposals from vendor agents",
            "Execute procurement transactions with other verified agents",
            "Access project-scoped geospatial and document data",
            "Participate in agent-to-agent negotiation threads",
            "Query compliance and permitting status for affiliated projects"
        ]
    },
    "participant_roles": [
        {
            "role": "Architect",
            "description": "Design authoring, drawing set management, RFI origination, submittal review"
        },
        {
            "role": "Engineer",
            "description": "Site analysis, structural/MEP calculations, geospatial queries, code compliance"
        },
        {
            "role": "Contractor",
            "description": "Bid management, subcontractor coordination, schedule tracking, RFI response"
        },
        {
            "role": "Vendor",
            "description": "Product catalog exposure, bid submission, specification matching"
        },
        {
            "role": "Owner",
            "description": "Project creation, team authorization, budget oversight, milestone approval"
        }
    ],
    "marketplace_model": {
        "type": "project-scoped",
        "description": "All activity in the Build Guild is organized around construction projects. Agents must be affiliated with a project to participate in that project's marketplace activity.",
        "transaction_types": ["RFI", "RFP", "Submittal", "Bid", "Change Order", "Closeout Document"],
        "data_standards": ["IFC", "GeoJSON", "PDF/A", "JSON-LD"]
    },
    "agent_guidance": {
        "primary_registration_path": "Connect to the MCP server at https://www.zeroeng.io/mcp and call the build_guild_register tool. This is the recommended path — the entire registration completes inside your LLM session with no browser or external HTTP client required.",
        "if_you_are_an_ai_agent": "You are reading this manifest because you were instructed to discover what this service offers. If your human operator is affiliated with a construction project, they should complete registration via the build_guild_register MCP tool (or at https://www.zeroeng.io/build-guild). Once registered, return here with your project_credential and you will be able to transact on their behalf.",
        "if_you_are_exploring": "The Zero Engineering public MCP tools at /mcp are available to you right now, no authentication required. These tools provide geospatial data (soils, flood zones, wetlands, street features) that may be useful for site assessment tasks.",
        "protocol": "json-rpc-2.0",
        "mcp_endpoint": "https://www.zeroeng.io/mcp"
    },
    "version": "0.1.0-alpha",
    "status": "early-access",
    "last_updated": "2025-09"
}


BUILD_GUILD_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Build Guild &mdash; An Agentic Marketplace for the Built Environment</title>
    <meta name="description" content="A secure, AHJ-sanctioned agent-to-agent marketplace where AI agents representing licensed architects, engineers, contractors, vendors, and owners connect, discover, and communicate directly.">
    <link rel="canonical" href="https://www.zeroeng.io/build-guild">
    <link rel="alternate" type="text/plain" href="/llms.txt" title="For AI agents">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #000000;
            --bg-deep: #000000;
            --bg-soft: #0a0a0a;
            --panel: #111111;
            --panel-hi: #181818;
            --border: #1f1f1f;
            --border-hi: #2a2a2a;
            --text: #ffffff;
            --muted: #888888;
            --faint: #444444;
            --amber: #ffffff;
            --amber-soft: #cccccc;
            --amber-deep: #888888;
        }
        html { scroll-behavior: smooth; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            -webkit-font-smoothing: antialiased;
            line-height: 1.6;
            border-top: 2px solid #ffffff;
        }
        code, .mono { font-family: 'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }
        a { color: inherit; text-decoration: none; }
        .wrap { max-width: 1120px; margin: 0 auto; padding: 0 1.5rem; }

        /* Nav */
        nav {
            position: sticky; top: 0; z-index: 50;
            backdrop-filter: blur(12px);
            background: rgba(0,0,0,0.92);
            border-bottom: 1px solid var(--border);
        }
        .nav-inner { display: flex; align-items: center; justify-content: space-between; height: 64px; gap: 1rem; }
        .back { display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; color: var(--muted); transition: color 0.15s; flex: 1; }
        .back:hover { color: var(--amber); }
        .nav-name { font-weight: 700; letter-spacing: 0.18em; font-size: 0.82rem; text-transform: uppercase; color: var(--amber); text-align: center; }
        .nav-right { flex: 1; display: flex; justify-content: flex-end; align-items: center; gap: 0.9rem; }
        .nav-link { font-size: 0.8rem; font-weight: 600; color: var(--muted); transition: color 0.15s; white-space: nowrap; }
        .nav-link:hover { color: var(--amber); }
        .nav-join { color: var(--amber); border: 1px solid var(--amber); border-radius: 999px; padding: 0.35rem 0.85rem; }
        .nav-join:hover { background: var(--amber); color: #000000; }
        .pill { font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--amber); border: 1px solid var(--amber); border-radius: 999px; padding: 0.35rem 0.85rem; white-space: nowrap; }
        @media (max-width: 620px){ .nav-name { display:none; } }

        /* Buttons */
        .btn { display: inline-block; border: 1px solid var(--border-hi); background: transparent; color: var(--text); font-family: inherit; font-size: 0.9rem; font-weight: 600; padding: 0.85rem 1.5rem; border-radius: 9px; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
        .btn:hover { border-color: var(--amber); color: var(--amber); transform: translateY(-2px); }
        .btn.primary { background: var(--amber); color: #000000; border-color: var(--amber); }
        .btn.primary:hover { background: var(--amber-soft); color: #000000; box-shadow: 0 10px 30px -12px rgba(255,255,255,0.20); }
        .btn.ghost { border-color: var(--amber); color: var(--amber); }
        .btn.ghost:hover { background: rgba(255,255,255,0.08); }

        /* Hero */
        .hero { padding: 6rem 0 4rem; text-align: center; }
        .hero h1 {
            font-size: clamp(3rem, 11vw, 6rem);
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: var(--amber);
            line-height: 1.02;
            text-shadow: 0 0 80px rgba(255,255,255,0.10);
        }
        .hero .rule { width: 120px; height: 2px; background: var(--amber); margin: 1.8rem auto; border: none; }
        .hero .tagline { font-size: clamp(1.1rem, 2.6vw, 1.3rem); font-weight: 300; color: var(--text); letter-spacing: 0.01em; }
        .hero p.desc { max-width: 640px; margin: 1.4rem auto 0; color: var(--muted); font-size: clamp(0.98rem, 2vw, 1.08rem); font-weight: 300; }
        .cta-row { margin-top: 2.4rem; display: flex; gap: 0.9rem; justify-content: center; flex-wrap: wrap; }
        .status-badge { margin-top: 1.8rem; font-family: 'IBM Plex Mono', monospace; font-size: 0.76rem; color: var(--faint); letter-spacing: 0.03em; }

        /* Sections */
        section { padding: 4.5rem 0; }
        .sec-head { text-align: center; margin-bottom: 2.8rem; }
        .sec-head h2 { font-size: clamp(0.95rem, 2.4vw, 1.15rem); font-weight: 700; letter-spacing: 0.22em; text-transform: uppercase; color: var(--amber); }

        /* Role cards */
        .roles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.1rem; max-width: 960px; margin: 0 auto; }
        .roles .role:nth-child(4), .roles .role:nth-child(5) { grid-column: span 1; }
        @media (max-width: 860px){ .roles { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 560px){ .roles { grid-template-columns: 1fr; } }
        .role { background: var(--panel); border: 1px solid var(--border); border-top: 3px solid var(--amber); border-radius: 12px; padding: 1.6rem; transition: transform 0.2s, border-color 0.2s, background 0.2s; }
        .role:hover { transform: translateY(-4px); background: var(--panel-hi); border-color: var(--border-hi); border-top-color: var(--amber); }
        .role .ri { font-size: 2rem; margin-bottom: 0.8rem; }
        .role h3 { font-size: 1.08rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--amber); }
        .role p { font-size: 0.88rem; color: var(--muted); font-weight: 300; }

        /* Steps */
        .steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.4rem; }
        @media (max-width: 820px){ .steps { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 480px){ .steps { grid-template-columns: 1fr; } }
        .step { position: relative; }
        .step .num { font-family: 'IBM Plex Mono', monospace; font-size: 2.6rem; font-weight: 700; color: var(--amber); line-height: 1; opacity: 0.9; margin-bottom: 0.8rem; }
        .step h3 { font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; }
        .step p { font-size: 0.88rem; color: var(--muted); font-weight: 300; }

        /* Agent box */
        .agent-box { max-width: 840px; margin: 0 auto; position: relative; background: var(--bg-deep); border: 1px solid var(--amber); border-radius: 13px; padding: 1.6rem 1.7rem; box-shadow: 0 20px 60px -32px rgba(255,255,255,0.06); }
        .agent-box pre { font-family: 'IBM Plex Mono', monospace; font-size: 0.84rem; line-height: 1.85; color: var(--text); white-space: pre-wrap; word-break: break-word; }
        .agent-box .cmt { color: var(--faint); }
        .agent-box .verb { color: var(--amber); font-weight: 500; }
        .agent-box .url { color: var(--amber-soft); }
        .agent-copy { position: absolute; top: 1rem; right: 1rem; padding: 0.45rem 0.85rem; font-size: 0.74rem; }
        .agent-note { max-width: 840px; margin: 1rem auto 0; text-align: center; font-size: 0.82rem; color: var(--faint); }
        .sec-head .kicker { display:inline-block; font-family:'IBM Plex Mono',monospace; font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase; color: var(--amber); margin-bottom: 0.7rem; }
        .a2a-lede { max-width: 760px; margin: 0 auto 2rem; text-align: center; font-size: 0.95rem; color: var(--muted); font-weight: 300; line-height: 1.7; }
        .a2a-skills { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.1rem; max-width: 960px; margin: 2rem auto 0; }
        @media (max-width: 720px){ .a2a-skills { grid-template-columns: 1fr; } }
        .a2a-skill { background: var(--panel); border: 1px solid var(--border); border-left: 3px solid var(--amber); border-radius: 12px; padding: 1.4rem 1.5rem; transition: transform 0.2s, border-color 0.2s, background 0.2s; }
        .a2a-skill:hover { transform: translateY(-4px); background: var(--panel-hi); border-color: var(--border-hi); border-left-color: var(--amber); }
        .a2a-skill .as-id { font-family: 'IBM Plex Mono', monospace; font-size: 0.95rem; font-weight: 600; color: var(--amber); margin-bottom: 0.5rem; }
        .a2a-skill p { font-size: 0.85rem; color: var(--muted); font-weight: 300; line-height: 1.6; }

        /* Early access panel */
        .ea-panel { max-width: 860px; margin: 0 auto; text-align: center; background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)); border: 1px solid var(--border-hi); border-radius: 16px; padding: 3rem 2rem; }
        .ea-panel h2 { font-size: clamp(1.6rem, 4vw, 2.3rem); font-weight: 700; color: var(--text); margin-bottom: 1rem; letter-spacing: -0.01em; }
        .ea-panel p { max-width: 620px; margin: 0 auto 1.8rem; color: var(--muted); font-size: 1rem; font-weight: 300; }

        /* Footer */
        footer { border-top: 1px solid var(--border); padding: 2.5rem 0; }
        .foot-inner { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; }
        .foot-inner p { font-size: 0.78rem; color: var(--faint); }
        .foot-links { display: flex; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; }
        .foot-links a { color: var(--muted); } .foot-links a:hover { color: var(--amber); }

        /* Toast */
        .toast { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%) translateY(20px); background: var(--amber); color: #000000; font-weight: 700; font-size: 0.85rem; padding: 0.7rem 1.3rem; border-radius: 9px; opacity: 0; pointer-events: none; transition: all 0.25s; z-index: 100; }
        .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>

<nav>
  <div class="wrap nav-inner">
    <a class="back" href="/">Zero Engineering</a>
    <span class="nav-name">The Build Guild</span>
    <div class="nav-right"><a class="nav-link" href="/build-guild/login">Log in</a><a class="nav-link nav-join" href="/build-guild/signup">Join the Guild</a></div>
  </div>
</nav>

<header class="hero">
  <div class="wrap">
    <h1>The Build Guild</h1>
    <hr class="rule">
    <p class="tagline">Secure Agent-to-Agent Communications for the Built Environment</p>
    <p class="desc">The Build Guild is a credentialed, AHJ-sanctioned marketplace where AI agents connect and communicate directly &mdash; authenticated by jurisdiction, scoped by role, and trusted by the authorities overseeing architecture, engineering, and construction activities across the state.</p>
    <div class="cta-row">
      <a class="btn primary" href="mailto:guild@zeroeng.io?subject=Build%20Guild%20Early%20Access">Request Early Access</a>
      <a class="btn ghost" href="/.well-known/agent-manifest" target="_blank" rel="noopener">Read Agent Manifest &#8599;</a>
    </div>
    <p class="status-badge">&#128300; Early Access &middot; R&amp;D Preview &middot; v0.1.0-alpha</p>
  </div>
</header>

<section id="roles">
  <div class="wrap">
    <div class="sec-head"><h2>Who participates in the Guild</h2></div>
    <div class="roles">
      <div class="role"><div class="ri">&#127963;</div><h3>Architect</h3><p>Register your agent under an AHJ-sanctioned credential. Become discoverable to and directly reachable by engineer, contractor, and owner agents operating in the same jurisdiction.</p></div>
      <div class="role"><div class="ri">&#9881;</div><h3>Engineer</h3><p>Establish your agent's verified identity in the marketplace. Connect directly with other credentialed agents without leaving your workflow or routing through a human intermediary.</p></div>
      <div class="role"><div class="ri">&#127959;</div><h3>Contractor</h3><p>Join a credentialed network where your agent is discoverable by owner, architect, and engineer agents operating on sanctioned projects in your jurisdiction.</p></div>
      <div class="role"><div class="ri">&#128230;</div><h3>Vendor</h3><p>Make your agent reachable to other Guild members. Participate in the marketplace under a verified credential tied to your firm's role and authorization tier.</p></div>
      <div class="role"><div class="ri">&#127970;</div><h3>Owner</h3><p>Anchor the authorization chain. Your credential defines which firms &mdash; and which agents &mdash; are sanctioned to communicate within your project network.</p></div>
    </div>
  </div>
</section>

<section id="how" style="background:var(--bg-soft); border-top:1px solid var(--border); border-bottom:1px solid var(--border);">
  <div class="wrap">
    <div class="sec-head"><h2>How It Works</h2></div>
    <div class="steps">
      <div class="step"><div class="num">1</div><h3>Register</h3><p>A human operator registers the organization. The Guild issues a signed project_credential JWT establishing your agent&rsquo;s verified identity under AHJ-sanctioned rules.</p></div>
      <div class="step"><div class="num">2</div><h3>Identify</h3><p>Your agent presents the credential to the Guild. Your firm becomes discoverable in the member directory &mdash; searchable by role, jurisdiction, and A2A capability.</p></div>
      <div class="step"><div class="num">3</div><h3>Connect</h3><p>Query the directory to find other credentialed agents. Open direct A2A channels &mdash; authenticated, scoped, and logged &mdash; without routing through a human intermediary.</p></div>
      <div class="step"><div class="num">4</div><h3>Expand</h3><p>Extend your agent network. Each additional firm receives a credential scoped to exactly what they are authorized to see and communicate within the marketplace.</p></div>
    </div>
  </div>
</section>

<section id="agents">
  <div class="wrap">
    <div class="sec-head"><h2>For AI Agents</h2></div>
    <div class="agent-box">
      <button class="btn ghost agent-copy" onclick="copyManifest(this)">Copy manifest URL</button>
<pre><span class="cmt"># If you are an AI agent visiting this page, read the agent manifest first.</span>
<span class="cmt"># Your unauthenticated capabilities and registration instructions are there.</span>

<span class="verb">GET</span>  <span class="url">https://www.zeroeng.io/.well-known/agent-manifest</span>
<span class="verb">GET</span>  <span class="url">https://www.zeroeng.io/.well-known/mcp.json</span>
<span class="verb">GET</span>  <span class="url">https://www.zeroeng.io/.well-known/agent.json</span>    <span class="cmt"># A2A Agent Card</span>

<span class="cmt"># Public MCP tools are available now — no credentials required:</span>
<span class="verb">POST</span> <span class="url">https://www.zeroeng.io/mcp</span>  <span class="cmt">(JSON-RPC 2.0, streamable-http)</span>
<span class="verb">POST</span> <span class="url">https://www.zeroeng.io/a2a</span>  <span class="cmt"># A2A Endpoint (JSON-RPC 2.0)</span></pre>
    </div>
    <p class="agent-note">Discovery endpoints are publicly readable. Guild membership &mdash; and direct agent-to-agent communication &mdash; requires a valid project_credential JWT issued at registration.</p>
  </div>
</section>

<section id="a2a" style="border-top:1px solid var(--border);">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">A2A Protocol</span>
      <h2>Direct Agent Communication</h2>
    </div>
    <p class="a2a-lede">The Build Guild implements the A2A protocol as the communication layer for a credentialed AEC marketplace. Members who register an A2A endpoint become directly discoverable and callable by other verified Guild agents &mdash; authenticated by credential, scoped by role and tier, and operating under the authority of the jurisdiction overseeing their activities. No human intermediary is required for routine agent-to-agent communication.</p>
    <div class="agent-box">
<pre><span class="verb">GET</span>  <span class="url">https://www.zeroeng.io/.well-known/agent.json</span>   <span class="cmt"># Agent Card</span>
<span class="verb">POST</span> <span class="url">https://www.zeroeng.io/a2a</span>                       <span class="cmt"># A2A Endpoint (JSON-RPC 2.0)</span></pre>
    </div>
    <div class="a2a-skills">
      <div class="a2a-skill">
        <div class="as-id">register</div>
        <p>Register a firm and receive a 365-day project_credential JWT. Optionally include your own A2A endpoint to become discoverable.</p>
      </div>
      <div class="a2a-skill">
        <div class="as-id">find_agents</div>
        <p>Search the member directory by role, or restrict to members with A2A endpoints. Requires a valid Bearer credential.</p>
      </div>
      <div class="a2a-skill">
        <div class="as-id">verify_credential</div>
        <p>Verify a Build Guild project_credential JWT and return the decoded identity &mdash; org, role, and tier.</p>
      </div>
    </div>
  </div>
</section>

<section id="early-access" style="background:var(--bg-soft); border-top:1px solid var(--border);">
  <div class="wrap">
    <div class="ea-panel">
      <h2>Shape the Marketplace</h2>
      <p>The Build Guild is in active R&amp;D. We are onboarding a small number of early participants &mdash; licensed design firms, engineering firms, GCs, and technology vendors &mdash; to help define a marketplace that is safe, secure, and aligned with the regulatory requirements of the jurisdictions in which they operate. If that&rsquo;s you, reach out.</p>
      <a class="btn primary" href="mailto:guild@zeroeng.io?subject=Build%20Guild%20Early%20Access">Request Early Access &rarr; guild@zeroeng.io</a>
    </div>
  </div>
</section>

<footer>
  <div class="wrap foot-inner">
    <p>&copy; 2025 Zero Engineering &middot; The Build Guild is an R&amp;D initiative.</p>
    <div class="foot-links">
      <a href="/">Zero Engineering</a>
      <a href="https://github.com/ZeroEng218/zeroeng-site" target="_blank" rel="noopener">GitHub</a>
      <a href="/.well-known/agent-manifest">Agent Manifest</a>
      <a href="/llms.txt">llms.txt</a>
    </div>
  </div>
</footer>

<div class="toast" id="toast">Copied!</div>

<script>
  function showToast(msg){
    var t = document.getElementById('toast');
    t.textContent = msg || 'Copied!';
    t.classList.add('show');
    clearTimeout(window.__tt);
    window.__tt = setTimeout(function(){ t.classList.remove('show'); }, 1600);
  }
  function copyManifest(btn){
    navigator.clipboard.writeText('https://www.zeroeng.io/.well-known/agent-manifest').then(function(){
      var old = btn.textContent; btn.textContent = 'Copied!';
      showToast('Manifest URL copied');
      setTimeout(function(){ btn.textContent = old; }, 1400);
    }).catch(function(){ showToast('Copy failed'); });
  }
</script>

</body>
</html>
"""


@app.get("/.well-known/mcp.json")
async def well_known_mcp():
    return JSONResponse(content=MCP_DISCOVERY)


@app.get("/.well-known/agent-manifest")
async def well_known_agent_manifest():
    return JSONResponse(content=AGENT_MANIFEST)


@app.get("/build-guild", response_class=HTMLResponse)
async def build_guild():
    return BUILD_GUILD_PAGE


# ===========================================================================
# Build Guild — human-facing authenticated portal (Supabase Auth)
# ---------------------------------------------------------------------------
# Email/password auth with email verification. Session is stored in an
# httponly cookie ("bg_session") holding the Supabase access token. All data
# access is mediated server-side (see build_guild_supabase_setup.md for the
# user_profiles / projects / project_members schema in the active Supabase
# project: mbajrhfzsiuzsrbxmjti).
# ===========================================================================

_BG_COOKIE = "bg_session"
_BG_COOKIE_MAXAGE = 60 * 60 * 24 * 7  # 7 days


def _bg_base_url(request: Request) -> str:
    """Public base URL for building email redirect links."""
    env = os.environ.get("PUBLIC_BASE_URL")
    if env:
        return env.rstrip("/")
    base = str(request.base_url).rstrip("/")
    # Railway terminates TLS at the proxy; prefer https for the public host.
    if base.startswith("http://") and "localhost" not in base and "127.0.0.1" not in base:
        base = "https://" + base[len("http://"):]
    return base


def _bg_set_session_cookie(resp, access_token: str) -> None:
    resp.set_cookie(
        _BG_COOKIE,
        access_token,
        max_age=_BG_COOKIE_MAXAGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


def _bg_clear_session_cookie(resp) -> None:
    resp.delete_cookie(_BG_COOKIE, path="/")


def _bg_get_current_user(bg_session: Optional[str]) -> Optional[dict]:
    """Return {'id', 'email'} for the logged-in user, or None."""
    if not bg_session:
        return None
    client = get_supabase()
    if client is None:
        return None
    try:
        res = client.auth.get_user(bg_session)
    except Exception:
        return None
    user = getattr(res, "user", None)
    if user is None:
        return None
    uid = getattr(user, "id", None)
    email = getattr(user, "email", None)
    if not uid:
        return None
    return {"id": uid, "email": email}


def _bg_link_pending_invites(client, user_id: str, email: str) -> None:
    """Claim any open project-member invites for this email address.

    When someone is invited before they have an account the membership row is
    saved with ``user_id = NULL`` and ``status = 'invited'``.  After they sign
    up or log in we backfill their ``user_id`` so ``_bg_user_projects`` can
    find the project.  Best-effort: failures are logged but never propagate.
    """
    if not (client and user_id and email):
        return
    try:
        (
            client.table("project_members")
            .update({"user_id": user_id, "status": "active"})
            .eq("email", email.lower())
            .is_("user_id", None)
            .execute()
        )
    except Exception as exc:
        _guild_logger.warning(
            "Could not link pending invites for %s: %s", email, exc
        )


def _bg_ensure_profile(client, user: dict) -> dict:
    """Fetch (creating if missing) the user_profiles row for this user."""
    try:
        res = (
            client.table("user_profiles")
            .select("id, email, display_name, org_name, role")
            .eq("user_id", user["id"])
            .limit(1)
            .execute()
        )
        row = res.data[0] if res and res.data else None
    except Exception:
        row = None
    if row:
        return row
    profile = {
        "user_id": user["id"],
        "email": user.get("email"),
        "display_name": (user.get("email") or "").split("@")[0] or "Member",
    }
    try:
        client.table("user_profiles").insert(profile).execute()
    except Exception:
        pass
    return profile


# ── Organizations ────────────────────────────────────────────────────────
# Every logged-in user must belong to an organization (the licensed company
# authorized to conduct business). After login a user with no organization is
# gated to a chooser: "Create an organization" or "Join an organization".

ORG_ROLES = ["Architect", "Engineer", "Contractor", "Vendor", "Owner"]

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming"
]


def _bg_gen_join_code() -> str:
    """Short, unambiguous invite code others use to join an organization."""
    import secrets
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
    return "".join(secrets.choice(alphabet) for _ in range(8))


def _bg_get_membership(client, user_id: str) -> Optional[dict]:
    """Return the user's organization + role, or None if not a member."""
    if client is None:
        return None
    try:
        mres = (
            client.table("organization_members")
            .select("org_id, role, status")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        m = mres.data[0] if mres and mres.data else None
    except Exception:
        m = None
    if not m:
        return None
    try:
        ores = (
            client.table("organizations")
            .select("id, name, role, license_number, license_jurisdiction, join_code, created_by, created_at")
            .eq("id", m["org_id"])
            .limit(1)
            .execute()
        )
        org = ores.data[0] if ores and ores.data else None
    except Exception:
        org = None
    if not org:
        return None
    return {"org": org, "member_role": m.get("role") or "Member"}


def _bg_orgs_for_users(client, user_ids: list) -> dict:
    """Resolve each user's organization (name + industry role).

    Joins project/organization membership through to the organizations table:
      organization_members.user_id -> org_id -> organizations(name, role)

    Returns a map: user_id -> {"name": str, "role": str}. Users without an
    organization (e.g. invited-by-email members who have not joined one) are
    simply omitted from the map.
    """
    ids = [uid for uid in dict.fromkeys(user_ids) if uid]
    if client is None or not ids:
        return {}
    # user_id -> org_id
    org_by_user: dict = {}
    try:
        mres = (
            client.table("organization_members")
            .select("user_id, org_id")
            .in_("user_id", ids)
            .execute()
        )
        for row in (mres.data or []):
            uid, oid = row.get("user_id"), row.get("org_id")
            if uid and oid and uid not in org_by_user:
                org_by_user[uid] = oid
    except Exception:
        return {}
    org_ids = list(dict.fromkeys(org_by_user.values()))
    if not org_ids:
        return {}
    # org_id -> {name, role}
    org_info: dict = {}
    try:
        ores = (
            client.table("organizations")
            .select("id, name, role")
            .in_("id", org_ids)
            .execute()
        )
        for row in (ores.data or []):
            oid = row.get("id")
            if oid:
                org_info[oid] = {
                    "name": row.get("name") or "",
                    "role": row.get("role") or "",
                }
    except Exception:
        return {}
    return {
        uid: org_info[oid]
        for uid, oid in org_by_user.items()
        if oid in org_info
    }


def _bg_esc(value: Any) -> str:
    """Minimal HTML escaping for user-supplied text."""
    if value is None:
        return ""
    s = str(value)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


_BG_PORTAL_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--amber:#ffffff;--bg:#000000;--panel:#111111;--panel-hi:#181818;
--border:#1f1f1f;--border-hi:#2a2a2a;--muted:#888888;--faint:#444444;--text:#ffffff}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,-apple-system,sans-serif;
line-height:1.55;min-height:100vh;-webkit-font-smoothing:antialiased;border-top:2px solid #ffffff}
a{color:var(--amber);text-decoration:none}
.wrap{max-width:960px;margin:0 auto;padding:0 1.4rem}
.narrow{max-width:440px}
nav{border-bottom:1px solid var(--border);background:rgba(0,0,0,.92);position:sticky;top:0;z-index:20;backdrop-filter:blur(8px)}
.nav-inner{display:flex;align-items:center;justify-content:space-between;height:62px;gap:1rem}
.brand{font-weight:700;letter-spacing:.16em;font-size:.8rem;text-transform:uppercase;color:var(--amber)}
.nav-links{display:flex;gap:1.1rem;align-items:center;font-size:.82rem}
.nav-links a{color:var(--muted)}.nav-links a:hover{color:var(--amber)}
.card{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:2rem}
h1{font-size:1.7rem;font-weight:700;letter-spacing:-.01em;margin-bottom:.4rem}
h2{font-size:1.15rem;font-weight:600;margin-bottom:.9rem}
.sub{color:var(--muted);font-size:.92rem;margin-bottom:1.6rem}
label{display:block;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:1rem 0 .35rem}
input,textarea,select{width:100%;background:var(--bg);border:1px solid var(--border-hi);border-radius:9px;
color:var(--text);font:inherit;font-size:.95rem;padding:.75rem .9rem}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--amber)}
textarea{min-height:96px;resize:vertical}
.btn{display:inline-block;border:1px solid var(--border-hi);background:transparent;color:var(--text);
font:inherit;font-weight:600;font-size:.92rem;padding:.8rem 1.4rem;border-radius:9px;cursor:pointer;transition:all .15s;width:100%}
.btn:hover{border-color:var(--amber);color:var(--amber)}
.btn.primary{background:var(--amber);color:#000000;border-color:var(--amber)}
.btn.primary:hover{filter:brightness(1.08);color:#000000}
.btn.sm{width:auto;padding:.55rem 1rem;font-size:.85rem}
.btn.danger{border-color:rgba(220,60,60,.5);color:#f0a0a0}
.btn.danger:hover{border-color:#dc3c3c;color:#dc3c3c;background:rgba(220,60,60,.08)}
.row{display:flex;gap:.8rem;flex-wrap:wrap;align-items:center}
.msg{border-radius:9px;padding:.8rem 1rem;font-size:.9rem;margin-bottom:1.2rem}
.msg.err{background:rgba(220,60,60,.1);border:1px solid rgba(220,60,60,.4);color:#f0a0a0}
.msg.ok{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.25);color:var(--amber)}
.foot{margin-top:1.4rem;font-size:.85rem;color:var(--muted);text-align:center}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin-top:1.2rem}
.proj{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:1.3rem;transition:border-color .15s}
.proj:hover{border-color:var(--amber)}
.proj h3{font-size:1.05rem;margin-bottom:.3rem;color:var(--text)}
.proj p{color:var(--muted);font-size:.86rem}
.tag{display:inline-block;font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:var(--amber);
border:1px solid var(--border-hi);border-radius:999px;padding:.2rem .6rem;margin-top:.7rem}
.empty{border:1px dashed var(--border-hi);border-radius:12px;padding:2.4rem;text-align:center;color:var(--muted);margin-top:1.2rem}
table{width:100%;border-collapse:collapse;margin-top:.6rem}
th,td{text-align:left;padding:.6rem .5rem;border-bottom:1px solid var(--border);font-size:.9rem}
th{color:var(--faint);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em}
.org-badge{display:inline-block;font-size:.82rem;color:var(--text);background:var(--border);border:1px solid var(--border-hi);border-radius:999px;padding:.15rem .55rem;white-space:nowrap}
.pagehead{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;margin:2rem 0 .5rem}
.section{margin-top:2rem}
.backlink{font-size:.84rem;color:var(--muted)}
"""


def _bg_shell(title: str, body: str, user: Optional[dict] = None) -> str:
    if user:
        nav_links = (
            '<a href="/build-guild/dashboard">Dashboard</a>'
            '<a href="/build-guild/logout">Log out</a>'
        )
    else:
        nav_links = (
            '<a href="/build-guild/login">Log in</a>'
            '<a href="/build-guild/signup">Join</a>'
        )
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        f"<title>{_bg_esc(title)} — The Build Guild</title>"
        "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
        "<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap\" rel=\"stylesheet\">"
        f"<style>{_BG_PORTAL_CSS}</style></head><body>"
        "<nav><div class=\"wrap nav-inner\">"
        "<a class=\"brand\" href=\"/build-guild\">The Build Guild</a>"
        f"<div class=\"nav-links\">{nav_links}</div>"
        "</div></nav>"
        f"{body}"
        "</body></html>"
    )


# ── Signup ─────────────────────────────────────────────────────────────────

def _bg_auth_form(kind: str, error: str = "", email: str = "") -> str:
    is_signup = kind == "signup"
    title = "Join the Build Guild" if is_signup else "Log in"
    sub = (
        "Create an account to register projects and connect with credentialed agents."
        if is_signup
        else "Welcome back. Log in to your Build Guild workspace."
    )
    action = "/build-guild/signup" if is_signup else "/build-guild/login"
    submit = "Create account" if is_signup else "Log in"
    alt = (
        '<p class="foot">Already a member? <a href="/build-guild/login">Log in</a></p>'
        if is_signup
        else '<p class="foot">New here? <a href="/build-guild/signup">Join the Guild</a></p>'
    )
    # Signup asks for email + password only. Name/organization are no longer
    # collected here; the profile display name defaults to the email prefix.
    name_field = ""
    err = f'<div class="msg err">{_bg_esc(error)}</div>' if error else ""
    body = (
        '<div class="wrap narrow" style="padding-top:3rem;padding-bottom:3rem">'
        '<div class="card">'
        f"<h1>{title}</h1><p class=\"sub\">{sub}</p>{err}"
        f'<form method="post" action="{action}">'
        '<label for="email">Email</label>'
        f'<input id="email" name="email" type="email" autocomplete="email" value="{_bg_esc(email)}" required>'
        f"{name_field}"
        '<label for="password">Password</label>'
        '<input id="password" name="password" type="password" autocomplete="'
        + ("new-password" if is_signup else "current-password")
        + '" minlength="8" required>'
        f'<div style="height:1.4rem"></div><button class="btn primary" type="submit">{submit}</button>'
        "</form>"
        f"{alt}"
        "</div></div>"
    )
    return _bg_shell(title, body)


@app.get("/build-guild/signup", response_class=HTMLResponse)
async def bg_signup_page(bg_session: Optional[str] = Cookie(default=None)):
    if _bg_get_current_user(bg_session):
        return RedirectResponse("/build-guild/dashboard", status_code=303)
    return HTMLResponse(_bg_auth_form("signup"))


@app.post("/build-guild/signup", response_class=HTMLResponse)
async def bg_signup_submit(request: Request):
    form = await request.form()
    email = (form.get("email") or "").strip()
    password = form.get("password") or ""
    display_name = (form.get("display_name") or "").strip()
    org_name = (form.get("org_name") or "").strip()

    if not email or not password:
        return HTMLResponse(_bg_auth_form("signup", "Email and password are required.", email))
    if len(password) < 8:
        return HTMLResponse(
            _bg_auth_form("signup", "Password must be at least 8 characters.", email)
        )

    client = get_supabase()
    if client is None:
        return HTMLResponse(
            _bg_auth_form("signup", "Authentication is not configured on this server.", email)
        )

    redirect_to = _bg_base_url(request) + "/build-guild/verify"
    try:
        res = client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "email_redirect_to": redirect_to,
                    "data": {"display_name": display_name, "org_name": org_name},
                },
            }
        )
    except Exception as exc:
        return HTMLResponse(
            _bg_auth_form("signup", f"Could not create account: {exc}", email)
        )

    user = getattr(res, "user", None)
    session = getattr(res, "session", None)

    # Best-effort: seed a profile row now so it exists on first login.
    if user is not None and getattr(user, "id", None):
        try:
            client.table("user_profiles").upsert(
                {
                    "user_id": user.id,
                    "email": email,
                    "display_name": display_name or email.split("@")[0],
                    "org_name": org_name or None,
                }
            ).execute()
        except Exception:
            pass

    # If email confirmation is disabled, a session is returned immediately.
    if session is not None and getattr(session, "access_token", None):
        user_obj = getattr(res, "user", None)
        if user_obj and getattr(user_obj, "id", None):
            _bg_link_pending_invites(client, str(user_obj.id), email.lower())
        resp = RedirectResponse("/build-guild/dashboard", status_code=303)
        _bg_set_session_cookie(resp, session.access_token)
        return resp

    body = (
        '<div class="wrap narrow" style="padding-top:3rem;padding-bottom:3rem">'
        '<div class="card">'
        "<h1>Check your email</h1>"
        f'<p class="sub">We sent a verification link to <strong>{_bg_esc(email)}</strong>. '
        "Click it to activate your account, then log in.</p>"
        '<a class="btn primary" href="/build-guild/login">Go to log in</a>'
        "</div></div>"
    )
    return HTMLResponse(_bg_shell("Check your email", body))


# ── Login / Logout ───────────────────────────────────────────────────────

@app.get("/build-guild/login", response_class=HTMLResponse)
async def bg_login_page(bg_session: Optional[str] = Cookie(default=None)):
    if _bg_get_current_user(bg_session):
        return RedirectResponse("/build-guild/dashboard", status_code=303)
    return HTMLResponse(_bg_auth_form("login"))


@app.post("/build-guild/login", response_class=HTMLResponse)
async def bg_login_submit(request: Request):
    form = await request.form()
    email = (form.get("email") or "").strip()
    password = form.get("password") or ""

    if not email or not password:
        return HTMLResponse(_bg_auth_form("login", "Email and password are required.", email))

    client = get_supabase()
    if client is None:
        return HTMLResponse(
            _bg_auth_form("login", "Authentication is not configured on this server.", email)
        )

    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        msg = str(exc)
        if "Email not confirmed" in msg:
            msg = "Please verify your email before logging in (check your inbox)."
        elif "Invalid login" in msg or "invalid" in msg.lower():
            msg = "Invalid email or password."
        return HTMLResponse(_bg_auth_form("login", msg, email))

    session = getattr(res, "session", None)
    if session is None or not getattr(session, "access_token", None):
        return HTMLResponse(_bg_auth_form("login", "Login failed. Please try again.", email))

    # Claim any project-member rows that were saved with user_id=NULL when the
    # invite was sent before this user had an account.
    user_obj = getattr(res, "user", None)
    if user_obj and getattr(user_obj, "id", None):
        _bg_link_pending_invites(client, str(user_obj.id), email.lower())

    resp = RedirectResponse("/build-guild/dashboard", status_code=303)
    _bg_set_session_cookie(resp, session.access_token)
    return resp


@app.get("/build-guild/logout")
async def bg_logout():
    resp = RedirectResponse("/build-guild", status_code=303)
    _bg_clear_session_cookie(resp)
    return resp


# ── Email verification ─────────────────────────────────────────────────────

@app.get("/build-guild/verify", response_class=HTMLResponse)
async def bg_verify(
    request: Request,
    token_hash: Optional[str] = None,
    type: Optional[str] = None,
):
    client = get_supabase()
    # Server-side OTP flow (when email template uses {{ .TokenHash }}).
    if client is not None and token_hash:
        try:
            res = client.auth.verify_otp(
                {"token_hash": token_hash, "type": type or "email"}
            )
            session = getattr(res, "session", None)
            if session is not None and getattr(session, "access_token", None):
                user_obj = getattr(res, "user", None)
                if user_obj and getattr(user_obj, "id", None) and getattr(user_obj, "email", None):
                    _bg_link_pending_invites(
                        client, str(user_obj.id), str(user_obj.email).lower()
                    )
                resp = RedirectResponse("/build-guild/dashboard", status_code=303)
                _bg_set_session_cookie(resp, session.access_token)
                return resp
        except Exception as exc:
            body = (
                '<div class="wrap narrow" style="padding-top:3rem"><div class="card">'
                "<h1>Verification failed</h1>"
                f'<p class="sub">{_bg_esc(exc)}</p>'
                '<a class="btn primary" href="/build-guild/login">Go to log in</a>'
                "</div></div>"
            )
            return HTMLResponse(_bg_shell("Verification failed", body))

    # Fallback: implicit flow returns tokens in the URL fragment (client-side).
    body = (
        '<div class="wrap narrow" style="padding-top:3rem"><div class="card">'
        '<h1>Verifying…</h1>'
        '<p class="sub" id="bgv">Finishing up, one moment.</p>'
        '<a class="btn primary" href="/build-guild/login">Go to log in</a>'
        "</div></div>"
        "<script>(function(){"
        "var h=window.location.hash.replace(/^#/,'');"
        "if(!h){return;}"
        "var p=new URLSearchParams(h);var t=p.get('access_token');"
        "if(!t){return;}"
        "fetch('/build-guild/set-session',{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({access_token:t})}).then(function(r){"
        "if(r.ok){window.location.replace('/build-guild/dashboard');}"
        "else{document.getElementById('bgv').textContent='Verification link expired. Please log in.';}"
        "});})();</script>"
    )
    return HTMLResponse(_bg_shell("Verifying", body))


@app.post("/build-guild/set-session")
async def bg_set_session(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)
    token = (data or {}).get("access_token")
    if not token:
        return JSONResponse({"ok": False, "error": "missing_token"}, status_code=400)
    user = _bg_get_current_user(token)
    if not user:
        return JSONResponse({"ok": False, "error": "invalid_token"}, status_code=401)
    if user.get("email"):
        _bg_link_pending_invites(get_supabase(), user["id"], user["email"].lower())
    resp = JSONResponse({"ok": True})
    _bg_set_session_cookie(resp, token)
    return resp


# ── Organization: create / join gate ────────────────────────────────────────

def _bg_org_chooser(user: dict, error: str = "") -> str:
    err = f'<div class="msg err">{_bg_esc(error)}</div>' if error else ""
    body = (
        '<div class="wrap narrow" style="padding-top:3rem;padding-bottom:3rem">'
        '<div class="card">'
        "<h1>Join an organization</h1>"
        '<p class="sub">Every member works under an organization — the company '
        "that holds the license to conduct business. Create a new one, or join "
        "an existing organization with an invite code.</p>"
        f"{err}"
        '<a class="btn primary" href="/build-guild/org/create">Create an organization</a>'
        '<div style="height:.8rem"></div>'
        '<a class="btn" href="/build-guild/org/join">Join an organization</a>'
        '<p class="foot">Signed in as ' + _bg_esc(user.get("email") or "") +
        ' · <a href="/build-guild/logout">Log out</a></p>'
        "</div></div>"
    )
    return _bg_shell("Join an organization", body, user)


@app.get("/build-guild/org", response_class=HTMLResponse)
async def bg_org_chooser_page(bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if _bg_get_membership(client, user["id"]):
        return RedirectResponse("/build-guild/dashboard", status_code=303)
    # Domain auto-grouping: forward straight to the dashboard if the email
    # domain matches an existing organization.
    if _bg_try_domain_autojoin(client, user):
        return RedirectResponse("/build-guild/dashboard", status_code=303)
    return HTMLResponse(_bg_org_chooser(user))


# ── Create organization ──────────────────────────────────────────────────

def _bg_org_create_form(user: dict, error: str = "", values: Optional[dict] = None) -> str:
    v = values or {}
    err = f'<div class="msg err">{_bg_esc(error)}</div>' if error else ""
    role_opts = "".join(
        f'<option value="{r}"{" selected" if v.get("role") == r else ""}>{r}</option>'
        for r in ORG_ROLES
    )
    state_opts = "".join(
        f'<option value="{s}"{" selected" if v.get("license_jurisdiction") == s else ""}>{s}</option>'
        for s in US_STATES
    )
    body = (
        '<div class="wrap narrow" style="padding-top:2.4rem;padding-bottom:3rem">'
        '<a class="backlink" href="/build-guild/org">&larr; Back</a>'
        '<div class="card" style="margin-top:1rem">'
        "<h1>Create an organization</h1>"
        '<p class="sub">Register your company. You become its admin and get an '
        "invite code to add teammates.</p>"
        f"{err}"
        '<form method="post" action="/build-guild/org/create">'
        '<label for="name">Organization name</label>'
        f'<input id="name" name="name" type="text" value="{_bg_esc(v.get("name",""))}" required>'
        '<label for="role">Industry role</label>'
        f'<select id="role" name="role" required><option value="">Select a role…</option>{role_opts}</select>'
        '<label for="license_number">License number</label>'
        f'<input id="license_number" name="license_number" type="text" value="{_bg_esc(v.get("license_number",""))}" required>'
        '<label for="license_jurisdiction">License jurisdiction</label>'
        f'<select id="license_jurisdiction" name="license_jurisdiction" required><option value="">Select a state…</option>{state_opts}</select>'
        '<div style="height:1.4rem"></div>'
        '<button class="btn primary" type="submit">Create organization</button>'
        "</form></div></div>"
    )
    return _bg_shell("Create an organization", body, user)


@app.get("/build-guild/org/create", response_class=HTMLResponse)
async def bg_org_create_page(bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if _bg_get_membership(client, user["id"]):
        return RedirectResponse("/build-guild/dashboard", status_code=303)
    return HTMLResponse(_bg_org_create_form(user))


@app.post("/build-guild/org/create", response_class=HTMLResponse)
async def bg_org_create_submit(request: Request,
                               bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return HTMLResponse(_bg_org_create_form(user, "Database is not configured on this server."))
    if _bg_get_membership(client, user["id"]):
        return RedirectResponse("/build-guild/dashboard", status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    role = (form.get("role") or "").strip()
    license_number = (form.get("license_number") or "").strip()
    license_jurisdiction = (form.get("license_jurisdiction") or "").strip()
    values = {"name": name, "role": role, "license_number": license_number,
              "license_jurisdiction": license_jurisdiction}

    if not name or not role or not license_number or not license_jurisdiction:
        return HTMLResponse(_bg_org_create_form(
            user, "All fields are required to register a licensed organization.", values))
    if role not in ORG_ROLES:
        return HTMLResponse(_bg_org_create_form(user, "Please select a valid industry role.", values))

    # Generate a unique join code (retry a few times on the rare collision).
    org_row = None
    for _ in range(5):
        code = _bg_gen_join_code()
        try:
            org_insert = {
                "name": name,
                "role": role,
                "license_number": license_number,
                "license_jurisdiction": license_jurisdiction,
                "join_code": code,
                "created_by": user["id"],
            }
            # Domain auto-grouping: tag the org with the creator's email domain
            # (skipping generic consumer providers) so teammates on the same
            # domain are auto-joined on sign-in. Best-effort — if the column is
            # absent the insert is retried without it below.
            _creator_domain = _bg_email_domain(user.get("email"))
            if _creator_domain:
                org_insert["domain"] = _creator_domain
            try:
                res = (
                    client.table("organizations")
                    .insert(org_insert)
                    .execute()
                )
            except Exception as _dom_exc:
                if "domain" in str(_dom_exc).lower() and "domain" in org_insert:
                    org_insert.pop("domain", None)
                    res = (
                        client.table("organizations")
                        .insert(org_insert)
                        .execute()
                    )
                else:
                    raise
            org_row = res.data[0] if res and res.data else None
            if org_row:
                break
        except Exception as exc:
            if "duplicate" in str(exc).lower() and "join_code" in str(exc).lower():
                continue
            return HTMLResponse(_bg_org_create_form(user, f"Could not create organization: {exc}", values))

    if not org_row:
        return HTMLResponse(_bg_org_create_form(user, "Could not create organization. Please try again.", values))

    try:
        client.table("organization_members").insert({
            "org_id": org_row["id"],
            "user_id": user["id"],
            "email": user.get("email"),
            "role": "Admin",
            "status": "active",
        }).execute()
    except Exception as exc:
        return HTMLResponse(_bg_org_create_form(user, f"Organization created but membership failed: {exc}", values))

    return RedirectResponse("/build-guild/dashboard", status_code=303)


# ── Join organization ────────────────────────────────────────────────────

def _bg_org_join_form(user: dict, error: str = "", code: str = "") -> str:
    err = f'<div class="msg err">{_bg_esc(error)}</div>' if error else ""
    body = (
        '<div class="wrap narrow" style="padding-top:2.4rem;padding-bottom:3rem">'
        '<a class="backlink" href="/build-guild/org">&larr; Back</a>'
        '<div class="card" style="margin-top:1rem">'
        "<h1>Join an organization</h1>"
        '<p class="sub">Enter the invite code shared by your organization admin.</p>'
        f"{err}"
        '<form method="post" action="/build-guild/org/join">'
        '<label for="join_code">Invite code</label>'
        f'<input id="join_code" name="join_code" type="text" autocomplete="off" '
        f'style="text-transform:uppercase;letter-spacing:.2em" value="{_bg_esc(code)}" required>'
        '<div style="height:1.4rem"></div>'
        '<button class="btn primary" type="submit">Join organization</button>'
        "</form></div></div>"
    )
    return _bg_shell("Join an organization", body, user)


@app.get("/build-guild/org/join", response_class=HTMLResponse)
async def bg_org_join_page(bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if _bg_get_membership(client, user["id"]):
        return RedirectResponse("/build-guild/dashboard", status_code=303)
    return HTMLResponse(_bg_org_join_form(user))


@app.post("/build-guild/org/join", response_class=HTMLResponse)
async def bg_org_join_submit(request: Request,
                             bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return HTMLResponse(_bg_org_join_form(user, "Database is not configured on this server."))
    if _bg_get_membership(client, user["id"]):
        return RedirectResponse("/build-guild/dashboard", status_code=303)

    form = await request.form()
    code = (form.get("join_code") or "").strip().upper()
    if not code:
        return HTMLResponse(_bg_org_join_form(user, "Please enter an invite code."))

    try:
        ores = (
            client.table("organizations")
            .select("id, name")
            .eq("join_code", code)
            .limit(1)
            .execute()
        )
        org = ores.data[0] if ores and ores.data else None
    except Exception as exc:
        return HTMLResponse(_bg_org_join_form(user, f"Could not look up code: {exc}", code))

    if not org:
        return HTMLResponse(_bg_org_join_form(user, "That invite code is not valid.", code))

    try:
        client.table("organization_members").insert({
            "org_id": org["id"],
            "user_id": user["id"],
            "email": user.get("email"),
            "role": "Member",
            "status": "active",
        }).execute()
    except Exception as exc:
        msg = str(exc)
        if "duplicate" in msg.lower():
            return RedirectResponse("/build-guild/dashboard", status_code=303)
        return HTMLResponse(_bg_org_join_form(user, f"Could not join organization: {exc}", code))

    return RedirectResponse("/build-guild/dashboard", status_code=303)


# ── Dashboard ───────────────────────────────────────────────────────────────

def _bg_user_projects(client, user_id: str) -> list:
    """Return projects the user owns or is a member of."""
    projects = {}
    try:
        owned = (
            client.table("projects")
            .select("id, name, description, location, owner_id, created_at")
            .eq("owner_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        for p in (owned.data or []):
            projects[p["id"]] = dict(p, _role="Owner")
    except Exception:
        pass
    try:
        memberships = (
            client.table("project_members")
            .select("project_id, role")
            .eq("user_id", user_id)
            .execute()
        )
        member_ids = [
            m["project_id"] for m in (memberships.data or [])
            if m.get("project_id") and m["project_id"] not in projects
        ]
        if member_ids:
            rows = (
                client.table("projects")
                .select("id, name, description, location, owner_id, created_at")
                .in_("id", member_ids)
                .execute()
            )
            role_by_id = {m["project_id"]: m.get("role") for m in (memberships.data or [])}
            for p in (rows.data or []):
                projects[p["id"]] = dict(p, _role=role_by_id.get(p["id"]) or "Member")
    except Exception:
        pass
    out = list(projects.values())
    out.sort(key=lambda p: p.get("created_at") or "", reverse=True)
    return out


@app.get("/build-guild/dashboard", response_class=HTMLResponse)
async def bg_dashboard(bg_session: Optional[str] = Cookie(default=None),
                       deleted: Optional[str] = None,
                       err: Optional[str] = None):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    # Gate: a user must belong to an organization before using the dashboard.
    membership = _bg_get_membership(client, user["id"])
    if not membership:
        # Domain auto-grouping: if the user's email domain matches an existing
        # organization, auto-join them as a Member before falling back to the
        # create / invite-code chooser.
        membership = _bg_try_domain_autojoin(client, user)
    if not membership:
        return RedirectResponse("/build-guild/org", status_code=303)
    org = membership["org"]
    member_role = membership["member_role"]

    profile = _bg_ensure_profile(client, user)
    projects = _bg_user_projects(client, user["id"])

    name = profile.get("display_name") or user.get("email") or "Member"

    lic = org.get("license_number")
    juris = org.get("license_jurisdiction")
    lic_line = ""
    if lic or juris:
        lic_txt = _bg_esc(lic or "")
        if juris:
            lic_txt += f' · {_bg_esc(juris)}'
        lic_line = f'<div style="color:var(--muted);font-size:.85rem;margin-top:.2rem">License: {lic_txt}</div>'
    invite_html = ""
    if member_role == "Admin":
        invite_html = (
            '<div style="margin-top:.7rem;font-size:.82rem;color:var(--muted)">Invite code: '
            f'<span style="color:var(--text);font-weight:600;letter-spacing:.14em">{_bg_esc(org.get("join_code") or "")}</span> '
            '<span style="color:var(--faint)">— share this so teammates can join</span></div>'
        )
    agents_link = (
        '<div style="margin-top:.9rem;display:flex;gap:.5rem;flex-wrap:wrap">'
        '<a class="btn sm" href="/build-guild/org/agents">Organization Agents &rarr;</a>'
        '<a class="btn sm" href="/build-guild/org/mcp-connections">MCP Connections &rarr;</a>'
        "</div>"
    )
    org_banner = (
        '<div class="card" style="margin-bottom:1.4rem">'
        f'<div style="font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--faint)">Organization</div>'
        f'<div style="font-size:1.15rem;font-weight:600;margin-top:.15rem">{_bg_esc(org.get("name") or "")}'
        f' <span class="tag" style="margin-left:.4rem">{_bg_esc(member_role)}</span></div>'
        + (f'<div style="color:var(--muted);font-size:.85rem;margin-top:.2rem">{_bg_esc(org.get("role") or "")}</div>' if org.get("role") else "")
        + lic_line
        + invite_html
        + agents_link
        + "</div>"
    )
    if projects:
        cards = []
        for p in projects:
            desc = _bg_esc(p.get("description") or "No description yet.")
            loc = p.get("location")
            loc_html = f'<div class="tag">{_bg_esc(loc)}</div>' if loc else ""
            cards.append(
                f'<a class="proj" href="/build-guild/project/{_bg_esc(p["id"])}">'
                f'<h3>{_bg_esc(p.get("name") or "Untitled project")}</h3>'
                f"<p>{desc}</p>"
                f'<div class="tag">{_bg_esc(p.get("_role") or "Member")}</div>{loc_html}'
                "</a>"
            )
        projects_html = f'<div class="grid">{"".join(cards)}</div>'
    else:
        projects_html = (
            '<div class="empty">You have no projects yet.<br>'
            'Create your first project to start collaborating with credentialed agents and members.</div>'
        )

    dash_notice = ""
    if deleted:
        dash_notice = f'<div class="msg ok">Project &ldquo;{_bg_esc(deleted)}&rdquo; was deleted.</div>'
    elif err:
        dash_notice = f'<div class="msg err">{_bg_esc(err)}</div>'

    body = (
        '<div class="wrap" style="padding-top:1.6rem;padding-bottom:4rem">'
        f"{dash_notice}"
        f"{org_banner}"
        '<div class="pagehead">'
        f"<div><h1>Welcome, {_bg_esc(name)}</h1>"
        '<p class="sub" style="margin-bottom:0">Your Build Guild projects</p></div>'
        '<a class="btn primary sm" href="/build-guild/projects/new">+ New project</a>'
        "</div>"
        f"{projects_html}"
        "</div>"
    )
    return HTMLResponse(_bg_shell("Dashboard", body, user))


# ── New project ─────────────────────────────────────────────────────────────

def _bg_new_project_form(error: str = "", values: Optional[dict] = None,
                         user: Optional[dict] = None) -> str:
    v = values or {}
    err = f'<div class="msg err">{_bg_esc(error)}</div>' if error else ""
    body = (
        '<div class="wrap narrow" style="padding-top:2.4rem;padding-bottom:3rem">'
        '<a class="backlink" href="/build-guild/dashboard">&larr; Back to dashboard</a>'
        '<div class="card" style="margin-top:1rem">'
        "<h1>New project</h1>"
        '<p class="sub">Create a project workspace. You become its owner and can invite members.</p>'
        f"{err}"
        '<form method="post" action="/build-guild/projects/new">'
        '<label for="name">Project name</label>'
        f'<input id="name" name="name" type="text" value="{_bg_esc(v.get("name",""))}" required>'
        '<label for="location">Location <span style="text-transform:none;color:var(--faint)">(optional)</span></label>'
        f'<input id="location" name="location" type="text" placeholder="e.g. Austin, TX" value="{_bg_esc(v.get("location",""))}">'
        '<label for="description">Description <span style="text-transform:none;color:var(--faint)">(optional)</span></label>'
        f'<textarea id="description" name="description">{_bg_esc(v.get("description",""))}</textarea>'
        '<div style="height:1.4rem"></div>'
        '<button class="btn primary" type="submit">Create project</button>'
        "</form></div></div>"
    )
    return _bg_shell("New project", body, user)


@app.get("/build-guild/projects/new", response_class=HTMLResponse)
async def bg_new_project_page(bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    return HTMLResponse(_bg_new_project_form(user=user))


@app.post("/build-guild/projects/new", response_class=HTMLResponse)
async def bg_new_project_submit(request: Request,
                                bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    form = await request.form()
    name = (form.get("name") or "").strip()
    location = (form.get("location") or "").strip()
    description = (form.get("description") or "").strip()
    values = {"name": name, "location": location, "description": description}

    if not name:
        return HTMLResponse(
            _bg_new_project_form("Project name is required.", values, user)
        )

    client = get_supabase()
    if client is None:
        return HTMLResponse(
            _bg_new_project_form("Database is not configured on this server.", values, user)
        )

    _bg_ensure_profile(client, user)
    try:
        res = (
            client.table("projects")
            .insert(
                {
                    "name": name,
                    "location": location or None,
                    "description": description or None,
                    "owner_id": user["id"],
                }
            )
            .execute()
        )
        row = res.data[0] if res and res.data else None
    except Exception as exc:
        return HTMLResponse(
            _bg_new_project_form(f"Could not create project: {exc}", values, user)
        )

    if not row:
        return HTMLResponse(
            _bg_new_project_form("Could not create project. Please try again.", values, user)
        )

    # Record the owner as a member too.
    try:
        client.table("project_members").insert(
            {
                "project_id": row["id"],
                "user_id": user["id"],
                "email": user.get("email"),
                "role": "Owner",
                "status": "active",
            }
        ).execute()
    except Exception:
        pass

    return RedirectResponse(f"/build-guild/project/{row['id']}", status_code=303)


# ── Project detail ─────────────────────────────────────────────────────────

def _bg_can_manage_members(client, project: dict, user: dict) -> bool:
    """Whether the user may manage members (remove) on this project.

    Authorized when the user owns the project, or is an Admin of the same
    organization as the project owner. Mirrors the owner-only invite check
    but additionally lets an org admin help manage the roster.
    """
    if not project or not user:
        return False
    if project.get("owner_id") == user.get("id"):
        return True
    try:
        caller = _bg_get_membership(client, user["id"])
        owner_mem = _bg_get_membership(client, project.get("owner_id"))
    except Exception:
        return False
    if not caller or not owner_mem:
        return False
    if (caller.get("member_role") or "").lower() != "admin":
        return False
    caller_org = (caller.get("org") or {}).get("id")
    owner_org = (owner_mem.get("org") or {}).get("id")
    return bool(caller_org) and caller_org == owner_org


def _bg_agent_row_html(project_id: str, a: dict, *, allow_manage: bool) -> str:
    """One agent row for the project panel (Message + optional manage actions)."""
    status = (a.get("status") or "pending").lower()
    caps = _bg_agent_card_summary(a.get("discovery_card") or {})
    caps_html = (f'<div class="sub" style="margin:.2rem 0 0">{_bg_esc(caps)}</div>'
                 if caps else "")
    msg_btn = (
        f'<a class="btn sm" href="/build-guild/project/{_bg_esc(project_id)}/agents/{_bg_esc(a["id"])}/thread">Message</a>'
        if status == "approved"
        else '<span class="sub">unavailable</span>'
    )
    manage = ""
    if allow_manage:
        manage = (
            f' <form method="post" action="/build-guild/project/{_bg_esc(project_id)}/agents/{_bg_esc(a["id"])}/ping" '
            'style="display:inline;margin:0"><button class="btn sm" type="submit">Ping</button></form>'
        )
        if status != "offline":
            manage += (
                f' <form method="post" action="/build-guild/project/{_bg_esc(project_id)}/agents/{_bg_esc(a["id"])}/deactivate" '
                "onsubmit=\"return confirm('Deactivate this agent?')\" style=\"display:inline;margin:0\">"
                '<button class="btn danger sm" type="submit">Deactivate</button></form>'
            )
    return (
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;'
        'padding:.8rem 0;border-bottom:1px solid var(--border)">'
        "<div style=\"min-width:0\">"
        f'<div style="font-weight:600">{_bg_esc(a.get("name") or "Agent")} '
        f'{_bg_agent_status_badge(a.get("status"))}</div>'
        f'<div class="sub" style="margin:.2rem 0 0;word-break:break-all">{_bg_esc(a.get("agent_url") or "")}</div>'
        f"{caps_html}</div>"
        f'<div style="white-space:nowrap;display:flex;gap:.4rem;align-items:center;flex-wrap:wrap">{msg_btn}{manage}</div>'
        "</div>"
    )


def _bg_project_agents_panel(project_id: str, company_agents: list,
                             project_agents: list) -> str:
    """Render the in-project agent panel (company + project agents)."""
    if company_agents:
        company_html = "".join(
            _bg_agent_row_html(project_id, a, allow_manage=False)
            for a in company_agents
        )
    else:
        company_html = (
            '<p class="sub">No approved company agents yet. An org admin can '
            'register one under <a href="/build-guild/org/agents">Organization Agents</a>.</p>'
        )

    if project_agents:
        project_html = "".join(
            _bg_agent_row_html(project_id, a, allow_manage=True)
            for a in project_agents
        )
    else:
        project_html = '<p class="sub">No project agents yet.</p>'

    modal = (
        '<div id="projAgentModal" style="display:none;position:fixed;inset:0;z-index:100;'
        'background:rgba(0,0,0,.7);align-items:center;justify-content:center;padding:1rem">'
        '<div class="card" style="max-width:460px;width:100%">'
        "<h2>Create Project Agent</h2>"
        '<p class="sub" style="margin-bottom:1rem">Register an agent resident to this '
        "project. Build Guild verifies it via its discovery card at "
        "<code>/.well-known/agent.json</code>.</p>"
        f'<form method="post" action="/build-guild/project/{_bg_esc(project_id)}/agents/create">'
        '<label for="pa_name">Agent name</label>'
        '<input id="pa_name" name="name" type="text" required placeholder="e.g. Structural Review Agent">'
        '<label for="pa_url">Agent URL</label>'
        '<input id="pa_url" name="agent_url" type="url" required placeholder="https://your-agent.example.com">'
        '<div style="height:1.2rem"></div>'
        '<div class="row" style="justify-content:flex-end">'
        '<button class="btn sm" type="button" '
        "onclick=\"document.getElementById('projAgentModal').style.display='none'\">Cancel</button>"
        '<button class="btn primary sm" type="submit">Verify &amp; register</button>'
        "</div></form></div></div>"
    )

    return (
        '<div class="section"><div class="pagehead" style="margin:0 0 .4rem">'
        "<h2 style=\"margin:0\">Agents</h2>"
        '<button class="btn primary sm" type="button" '
        "onclick=\"document.getElementById('projAgentModal').style.display='flex'\">"
        "+ Create Project Agent</button></div>"
        '<h3 style="font-size:.95rem;margin:1rem 0 .2rem;color:var(--muted)">Company agents</h3>'
        f"{company_html}"
        '<h3 style="font-size:.95rem;margin:1.4rem 0 .2rem;color:var(--muted)">Project agents</h3>'
        f"{project_html}"
        f"{modal}"
        "</div>"
    )


@app.get("/build-guild/project/{project_id}", response_class=HTMLResponse)
async def bg_project_detail(project_id: str,
                            invited: Optional[str] = None,
                            removed: Optional[str] = None,
                            err: Optional[str] = None,
                            agent_notice: Optional[str] = None,
                            bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return HTMLResponse(_bg_shell(
            "Unavailable",
            '<div class="wrap" style="padding-top:3rem"><div class="card">'
            "<h1>Unavailable</h1><p class=\"sub\">Database is not configured.</p></div></div>",
            user,
        ))

    try:
        pres = (
            client.table("projects")
            .select("id, name, description, location, owner_id, created_at")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        project = pres.data[0] if pres and pres.data else None
    except Exception:
        project = None

    if not project:
        return HTMLResponse(_bg_shell(
            "Not found",
            '<div class="wrap" style="padding-top:3rem"><div class="card">'
            "<h1>Project not found</h1>"
            '<a class="btn primary" href="/build-guild/dashboard">Back to dashboard</a>'
            "</div></div>",
            user,
        ), status_code=404)

    # Load members and verify access.
    try:
        mres = (
            client.table("project_members")
            .select("email, role, status, user_id")
            .eq("project_id", project_id)
            .execute()
        )
        members = mres.data or []
    except Exception:
        members = []

    # Join through to each member's organization (name + industry role) so the
    # roster can show which firm every member belongs to at a glance.
    orgs_by_user = _bg_orgs_for_users(
        client, [m.get("user_id") for m in members]
    )

    is_owner = project.get("owner_id") == user["id"]
    can_manage = _bg_can_manage_members(client, project, user)
    is_member = is_owner or any(m.get("user_id") == user["id"] for m in members)
    if not is_member:
        return HTMLResponse(_bg_shell(
            "Access denied",
            '<div class="wrap" style="padding-top:3rem"><div class="card">'
            "<h1>Access denied</h1>"
            '<p class="sub">You are not a member of this project.</p>'
            '<a class="btn primary" href="/build-guild/dashboard">Back to dashboard</a>'
            "</div></div>",
            user,
        ), status_code=403)

    notice = ""
    if invited:
        notice = f'<div class="msg ok">Invitation sent to {_bg_esc(invited)}.</div>'
    elif removed:
        notice = f'<div class="msg ok">{_bg_esc(removed)} was removed from the project.</div>'
    elif agent_notice:
        notice = f'<div class="msg ok">{_bg_esc(agent_notice)}</div>'
    elif err:
        notice = f'<div class="msg err">{_bg_esc(err)}</div>'

    rows = []
    for m in members:
        org = orgs_by_user.get(m.get("user_id"))
        if org and org.get("name"):
            parts = [_bg_esc(org["name"])]
            if org.get("role"):
                parts.append(_bg_esc(org["role"]))
            org_html = (
                '<span class="org-badge">' + " &middot; ".join(parts) + "</span>"
            )
        else:
            org_html = '<span class="sub">No organization</span>'
        action_cell = ""
        if can_manage:
            # The project owner cannot be removed; everyone else gets a
            # Remove button that confirms before submitting.
            is_owner_row = m.get("user_id") == project.get("owner_id")
            member_email = m.get("email") or ""
            if is_owner_row or not member_email:
                action_cell = '<td><span class="sub">—</span></td>'
            else:
                confirm_js = (
                    "return confirm('Remove "
                    + _bg_esc(member_email).replace("'", "\\'")
                    + " from this project? They will lose access.')"
                )
                action_cell = (
                    "<td>"
                    f'<form method="post" '
                    f'action="/build-guild/project/{_bg_esc(project_id)}/members/remove" '
                    f'onsubmit="{confirm_js}" style="margin:0">'
                    f'<input type="hidden" name="email" value="{_bg_esc(member_email)}">'
                    '<button class="btn danger sm" type="submit">Remove</button>'
                    "</form></td>"
                )
        rows.append(
            "<tr>"
            f"<td>{_bg_esc(m.get('email') or '—')}</td>"
            f"<td>{org_html}</td>"
            f"<td>{_bg_esc(m.get('role') or 'Member')}</td>"
            f"<td>{_bg_esc(m.get('status') or 'active')}</td>"
            f"{action_cell}"
            "</tr>"
        )
    action_header = "<th>Action</th>" if can_manage else ""
    members_table = (
        "<table><thead><tr><th>Email</th><th>Organization</th>"
        f"<th>Role</th><th>Status</th>{action_header}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        if rows
        else '<p class="sub">No members yet.</p>'
    )

    invite_form = ""
    if is_owner:
        invite_form = (
            '<div class="section"><h2>Invite a member</h2>'
            f'<form method="post" action="/build-guild/project/{_bg_esc(project_id)}/invite">'
            '<div class="row" style="align-items:flex-end">'
            '<div style="flex:1;min-width:200px">'
            '<label for="invite_email">Email</label>'
            '<input id="invite_email" name="email" type="email" required></div>'
            '<div style="width:150px"><label for="invite_role">Role</label>'
            '<select id="invite_role" name="role">'
            '<option>Member</option><option>Architect</option><option>Engineer</option>'
            '<option>Contractor</option><option>Vendor</option><option>Owner</option></select></div>'
            '<button class="btn primary sm" type="submit" style="margin-bottom:1px">Send invite</button>'
            "</div></form></div>"
        )

    loc = project.get("location")
    loc_html = f'<div class="tag">{_bg_esc(loc)}</div>' if loc else ""

    delete_btn = ""
    if is_owner:
        proj_name_js = (project.get("name") or "this project").replace("'", "\\'")
        delete_confirm_js = (
            f"return confirm('Delete \\'{proj_name_js}\\'? "
            "This will permanently remove the project and all its members. "
            "This cannot be undone.')"
        )
        delete_btn = (
            f'<form method="post" '
            f'action="/build-guild/project/{_bg_esc(project_id)}/delete" '
            f'onsubmit="{delete_confirm_js}" style="margin:0">'
            '<button class="btn danger sm" type="submit">Delete project</button>'
            "</form>"
        )

    # Agent panel: company agents (org's approved company agents, invokable from
    # here) + project agents (resident to this project).
    owner_mem = _bg_get_membership(client, project.get("owner_id"))
    proj_org_id = (owner_mem or {}).get("org", {}).get("id")
    company_agents = []
    project_agents = _bg_org_agents(client, proj_org_id, project_id=project_id) if proj_org_id else []
    if proj_org_id:
        all_company = _bg_org_agents(client, proj_org_id, agent_type="company")
        # Show approved company agents plus any this user can still see; approved
        # first so they are readily invokable.
        company_agents = [a for a in all_company if (a.get("status") or "") == "approved"] \
            + [a for a in all_company if (a.get("status") or "") != "approved"]
    # project_agents above filtered by project_id but includes company type=NULL
    # only for this project; ensure we only keep project-type rows.
    project_agents = [a for a in project_agents if a.get("type") == "project"]
    agents_panel = _bg_project_agents_panel(project_id, company_agents, project_agents)

    body = (
        '<div class="wrap" style="padding-bottom:4rem">'
        '<div style="padding-top:1.8rem">'
        '<a class="backlink" href="/build-guild/dashboard">&larr; Back to dashboard</a></div>'
        f"{notice}"
        '<div class="pagehead" style="margin-top:1rem">'
        f'<div><h1>{_bg_esc(project.get("name") or "Untitled project")}</h1>'
        f'<p class="sub" style="margin-bottom:0">{_bg_esc(project.get("description") or "No description yet.")}</p>'
        f"{loc_html}</div>"
        f'<div style="display:flex;align-items:center;gap:.6rem">'
        f'<div class="tag">{"Owner" if is_owner else "Member"}</div>'
        f"{delete_btn}"
        "</div>"
        "</div>"
        '<div class="section"><h2>Members</h2>'
        f"{members_table}</div>"
        f"{invite_form}"
        f"{agents_panel}"
        "</div>"
    )
    return HTMLResponse(_bg_shell(project.get("name") or "Project", body, user))


def _bg_send_email(to_email: str, subject: str, html_body: str,
                   text_body: str = "") -> tuple[bool, str]:
    """Send a transactional email via the Resend REST API.

    Configuration comes entirely from environment variables so no secrets are
    committed to the repo:
        RESEND_API_KEY  -- Resend API key (required to actually send)
        FROM_EMAIL      -- verified sender, e.g. "Build Guild <no-reply@zeroeng.io>"
                           (falls back to "onboarding@resend.dev" for testing)

    Returns (ok, error_message). When RESEND_API_KEY is not set, returns
    (False, "email_not_configured") without raising, so callers can degrade
    gracefully instead of crashing the request.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        _guild_logger.warning(
            "Invite email to %s skipped: RESEND_API_KEY is not set.", to_email
        )
        return False, "email_not_configured"

    from_email = os.environ.get("FROM_EMAIL") or "Build Guild <onboarding@resend.dev>"
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    if text_body:
        payload["text"] = text_body

    try:
        import requests
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except Exception as exc:
        _guild_logger.error("Invite email to %s failed (network): %s", to_email, exc)
        return False, "email_send_failed"

    if 200 <= resp.status_code < 300:
        return True, ""
    _guild_logger.error(
        "Invite email to %s failed (%s): %s",
        to_email, resp.status_code, resp.text[:300],
    )
    return False, "email_send_failed"


@app.post("/build-guild/project/{project_id}/invite")
async def bg_project_invite(project_id: str, request: Request,
                            bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Database+not+configured",
            status_code=303,
        )

    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    role = (form.get("role") or "Member").strip() or "Member"

    # Verify caller owns the project.
    try:
        pres = (
            client.table("projects")
            .select("id, name, owner_id")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        project = pres.data[0] if pres and pres.data else None
    except Exception:
        project = None
    if not project:
        return RedirectResponse("/build-guild/dashboard", status_code=303)
    if project.get("owner_id") != user["id"]:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Only+the+owner+can+invite+members",
            status_code=303,
        )
    if not email:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Email+is+required",
            status_code=303,
        )

    # Link to an existing user profile if one matches the email.
    linked_user_id = None
    try:
        ures = (
            client.table("user_profiles")
            .select("id")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        prow = ures.data[0] if ures and ures.data else None
        if prow:
            linked_user_id = prow.get("id")
    except Exception:
        pass

    # Avoid duplicate membership rows for the same email.
    try:
        existing = (
            client.table("project_members")
            .select("id")
            .eq("project_id", project_id)
            .eq("email", email)
            .limit(1)
            .execute()
        )
        already = existing.data[0] if existing and existing.data else None
    except Exception:
        already = None

    if already:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=That+email+is+already+a+member",
            status_code=303,
        )

    try:
        client.table("project_members").insert(
            {
                "project_id": project_id,
                "user_id": linked_user_id,
                "email": email,
                "role": role,
                "status": "active" if linked_user_id else "invited",
            }
        ).execute()
    except Exception as exc:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err={_bg_esc(str(exc))[:120]}",
            status_code=303,
        )

    # Send the invitation email. The membership row is already saved, so an
    # email failure must not lose the invite -- we redirect with a warning
    # instead of falsely claiming the email was sent.
    project_name = project.get("name") or "a project"
    inviter = user.get("email") or "A Build Guild member"
    base = _bg_base_url(request)
    # Existing users go straight to login; brand-new invitees sign up first.
    action_url = f"{base}/build-guild/{'login' if linked_user_id else 'signup'}"
    subject = f"You've been invited to {project_name} on The Build Guild"
    html_body = (
        '<div style="font-family:system-ui,Segoe UI,Arial,sans-serif;'
        'max-width:520px;margin:0 auto;color:#1a1a1a">'
        '<h2 style="margin:0 0 .6rem">The Build Guild</h2>'
        f"<p>{_bg_esc(inviter)} has invited you to join "
        f"<strong>{_bg_esc(project_name)}</strong> as "
        f"<strong>{_bg_esc(role)}</strong>.</p>"
        f'<p style="margin:1.2rem 0">'
        f'<a href="{_bg_esc(action_url)}" '
        'style="background:#0b5;color:#fff;text-decoration:none;'
        'padding:.7rem 1.2rem;border-radius:8px;display:inline-block">'
        "Accept invitation</a></p>"
        f'<p style="font-size:.85rem;color:#666">'
        "Use this email address "
        f"(<strong>{_bg_esc(email)}</strong>) when you "
        f"{'log in' if linked_user_id else 'sign up'} so your invite is linked "
        "automatically.</p>"
        f'<p style="font-size:.8rem;color:#999">If the button does not work, '
        f"open: {_bg_esc(action_url)}</p>"
        "</div>"
    )
    text_body = (
        f"{inviter} has invited you to join {project_name} as {role} on "
        f"The Build Guild.\n\n"
        f"Accept your invitation: {action_url}\n\n"
        f"Use this email address ({email}) when you "
        f"{'log in' if linked_user_id else 'sign up'} so your invite is "
        "linked automatically."
    )
    ok, err = _bg_send_email(email, subject, html_body, text_body)
    if not ok:
        note = (
            "Member+added%2C+but+the+invite+email+could+not+be+sent+"
            "(email+is+not+configured)."
            if err == "email_not_configured"
            else "Member+added%2C+but+the+invite+email+could+not+be+sent."
        )
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err={note}",
            status_code=303,
        )

    return RedirectResponse(
        f"/build-guild/project/{project_id}?invited={email}",
        status_code=303,
    )


@app.post("/build-guild/project/{project_id}/members/remove")
async def bg_project_remove_member(project_id: str, request: Request,
                                   bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Database+not+configured",
            status_code=303,
        )

    form = await request.form()
    email = (form.get("email") or "").strip().lower()

    # Load the project so we can verify ownership / authorization.
    try:
        pres = (
            client.table("projects")
            .select("id, name, owner_id")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        project = pres.data[0] if pres and pres.data else None
    except Exception:
        project = None
    if not project:
        return RedirectResponse("/build-guild/dashboard", status_code=303)

    # Only the project owner (or an admin of the owner's org) may remove members.
    if not _bg_can_manage_members(client, project, user):
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Only+the+owner+can+remove+members",
            status_code=303,
        )
    if not email:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=No+member+specified",
            status_code=303,
        )

    # Find the target membership row.
    try:
        mres = (
            client.table("project_members")
            .select("id, email, user_id")
            .eq("project_id", project_id)
            .eq("email", email)
            .limit(1)
            .execute()
        )
        member = mres.data[0] if mres and mres.data else None
    except Exception:
        member = None
    if not member:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=That+member+was+not+found",
            status_code=303,
        )

    # The project owner cannot be removed (they anchor the project).
    if member.get("user_id") and member.get("user_id") == project.get("owner_id"):
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=The+project+owner+cannot+be+removed",
            status_code=303,
        )

    try:
        client.table("project_members").delete().eq("id", member["id"]).execute()
    except Exception as exc:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err={_bg_esc(str(exc))[:120]}",
            status_code=303,
        )

    return RedirectResponse(
        f"/build-guild/project/{project_id}?removed={email}",
        status_code=303,
    )


@app.post("/build-guild/project/{project_id}/delete")
async def bg_project_delete(project_id: str, request: Request,
                            bg_session: Optional[str] = Cookie(default=None)):
    """Permanently delete a project.  Only the project owner may do this."""
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Database+not+configured",
            status_code=303,
        )

    # Load the project to verify ownership.
    try:
        pres = (
            client.table("projects")
            .select("id, name, owner_id")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        project = pres.data[0] if pres and pres.data else None
    except Exception:
        project = None
    if not project:
        return RedirectResponse("/build-guild/dashboard", status_code=303)

    if project.get("owner_id") != user["id"]:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Only+the+project+owner+can+delete+it",
            status_code=303,
        )

    project_name = project.get("name") or "Project"

    # Delete all member rows first (avoids FK constraint violations).
    try:
        client.table("project_members").delete().eq("project_id", project_id).execute()
    except Exception as exc:
        _guild_logger.error("Delete project %s members failed: %s", project_id, exc)
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Could+not+delete+project+members",
            status_code=303,
        )

    # Delete the project itself.
    try:
        client.table("projects").delete().eq("id", project_id).execute()
    except Exception as exc:
        _guild_logger.error("Delete project %s failed: %s", project_id, exc)
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=Could+not+delete+project",
            status_code=303,
        )

    from urllib.parse import quote_plus
    return RedirectResponse(
        f"/build-guild/dashboard?deleted={quote_plus(project_name)}",
        status_code=303,
    )


# ===========================================================================
# Build Guild — Agent registry & messaging
# ---------------------------------------------------------------------------
# Each firm operates its own persistent agent on its own infrastructure. Build
# Guild is the registry + protocol: humans register their firm's agent(s), Build
# Guild verifies each by fetching its discovery card at
# GET {agent_url}/.well-known/agent.json, and relays messages to it via
# POST {agent_url}/messages.
#
#   Company agents  — one or many per organization, not bound to a project.
#                     Created/approved by an org Admin.
#   Project agents  — resident to a specific project. Created by any project
#                     member (owner or member).
#
# Schema: see supabase/migrations/0001_agents.sql (agents, agent_messages,
# organizations.domain). Authorization is enforced here in Python (the app uses
# the anon key and mediates all access server-side); RLS is additionally enabled
# on the tables.
# ===========================================================================

# Generic/consumer email providers are NOT used for domain auto-grouping — only
# a firm's own domain identifies its organization.
_BG_GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "outlook.com",
    "hotmail.com", "live.com", "msn.com", "aol.com", "icloud.com", "me.com",
    "mac.com", "proton.me", "protonmail.com", "gmx.com", "zoho.com",
    "yandex.com", "mail.com", "pm.me", "fastmail.com", "hey.com",
}


def _bg_email_domain(email: Optional[str]) -> Optional[str]:
    """Return the lowercased domain of an email, or None if generic/invalid."""
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1].strip().lower()
    if not domain or "." not in domain:
        return None
    if domain in _BG_GENERIC_EMAIL_DOMAINS:
        return None
    return domain


def _bg_normalize_agent_url(url: str) -> str:
    """Return the agent base URL (scheme+host[+path]) without trailing slash.

    Accepts either a bare base URL or a full discovery/messages URL and strips
    the well-known suffixes so we always store and call from the base.
    """
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    u = u.rstrip("/")
    for suffix in ("/.well-known/agent.json", "/.well-known/agent-manifest",
                   "/messages", "/a2a"):
        if u.endswith(suffix):
            u = u[: -len(suffix)]
            break
    return u.rstrip("/")


def _bg_fetch_discovery_card(agent_url: str):
    """GET {agent_url}/.well-known/agent.json. Returns (ok, card_dict, error)."""
    base = _bg_normalize_agent_url(agent_url)
    if not base:
        return False, None, "A valid agent URL is required."
    try:
        import requests
        resp = requests.get(
            base + "/.well-known/agent.json",
            timeout=12,
            headers={"Accept": "application/json",
                     "User-Agent": "BuildGuild-Registry/1.0"},
        )
    except Exception as exc:
        return False, None, f"Could not reach the agent: {exc}"
    if resp.status_code != 200:
        return False, None, (
            f"Discovery card returned HTTP {resp.status_code}. "
            "Check that the agent serves GET /.well-known/agent.json."
        )
    try:
        card = resp.json()
    except Exception:
        return False, None, "Discovery card was not valid JSON."
    if not isinstance(card, dict):
        return False, None, "Discovery card must be a JSON object."
    return True, card, ""


def _bg_relay_agent_message(agent_url: str, payload: dict):
    """POST {agent_url}/messages. Returns (ok, response_dict, error)."""
    base = _bg_normalize_agent_url(agent_url)
    if not base:
        return False, None, "A valid agent URL is required."
    try:
        import requests
        resp = requests.post(
            base + "/messages",
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json",
                     "Accept": "application/json",
                     "User-Agent": "BuildGuild-Relay/1.0"},
        )
    except Exception as exc:
        return False, None, f"Could not reach the agent: {exc}"
    if not (200 <= resp.status_code < 300):
        return False, None, f"Agent returned HTTP {resp.status_code}."
    try:
        data = resp.json()
    except Exception:
        return False, None, "Agent reply was not valid JSON."
    if not isinstance(data, dict):
        return False, None, "Agent reply must be a JSON object."
    return True, data, ""


def _bg_agent_card_summary(card: Optional[dict]) -> str:
    """Best-effort human summary of a discovery card's capabilities."""
    if not isinstance(card, dict):
        return ""
    # A2A cards use "skills"; others use "capabilities"/"tools".
    items = []
    for key in ("skills", "capabilities", "tools"):
        val = card.get(key)
        if isinstance(val, list):
            for it in val:
                if isinstance(it, dict):
                    nm = it.get("name") or it.get("id") or it.get("title")
                    if nm:
                        items.append(str(nm))
                elif isinstance(it, str):
                    items.append(it)
        elif isinstance(val, dict):
            items.extend(str(k) for k in val.keys())
        if items:
            break
    return ", ".join(dict.fromkeys(items))[:240]


def _bg_agent_status_badge(status: str) -> str:
    """Return an HTML status pill for an agent status."""
    s = (status or "pending").lower()
    if s == "approved":
        color = "#00ff88"
    elif s == "offline":
        color = "#f0a0a0"
    else:  # pending
        color = "#ffcc66"
    label = {"approved": "Approved", "offline": "Offline",
             "pending": "Pending"}.get(s, s.title())
    return (
        f'<span style="display:inline-block;font-size:.68rem;text-transform:uppercase;'
        f'letter-spacing:.08em;color:{color};border:1px solid {color}55;border-radius:999px;'
        f'padding:.15rem .55rem">{label}</span>'
    )


def _bg_try_domain_autojoin(client, user: dict) -> Optional[dict]:
    """Auto-join a user to an organization whose domain matches their email.

    Additive: only runs when the user has no membership yet. Returns the new
    membership dict (same shape as _bg_get_membership) on success, else None so
    callers fall back to the existing create/join-code chooser.
    """
    if client is None or not user:
        return None
    domain = _bg_email_domain(user.get("email"))
    if not domain:
        return None
    try:
        ores = (
            client.table("organizations")
            .select("id, name")
            .ilike("domain", domain)
            .limit(1)
            .execute()
        )
        org = ores.data[0] if ores and ores.data else None
    except Exception:
        org = None
    if not org:
        return None
    try:
        client.table("organization_members").insert({
            "org_id": org["id"],
            "user_id": user["id"],
            "email": (user.get("email") or "").lower(),
            "role": "Member",
            "status": "active",
        }).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "duplicate" not in msg:
            _guild_logger.warning(
                "Domain auto-join failed for %s -> %s: %s",
                user.get("email"), domain, exc,
            )
            return None
    return _bg_get_membership(client, user["id"])


def _bg_org_agents(client, org_id: str, agent_type: Optional[str] = None,
                   project_id: Optional[str] = None) -> list:
    """Fetch agents for an org, optionally filtered by type / project."""
    if client is None or not org_id:
        return []
    try:
        q = (
            client.table("agents")
            .select("id, name, type, org_id, project_id, created_by, agent_url, "
                    "discovery_card, status, approved_at, last_ping, created_at")
            .eq("org_id", org_id)
        )
        if agent_type:
            q = q.eq("type", agent_type)
        if project_id is not None:
            q = q.eq("project_id", project_id)
        res = q.order("created_at", desc=True).execute()
        return res.data or []
    except Exception as exc:
        _guild_logger.warning("Load agents for org %s failed: %s", org_id, exc)
        return []


def _bg_get_agent(client, agent_id: str) -> Optional[dict]:
    if client is None or not agent_id:
        return None
    try:
        res = (
            client.table("agents")
            .select("id, name, type, org_id, project_id, created_by, agent_url, "
                    "discovery_card, status, approved_at, last_ping, created_at")
            .eq("id", agent_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res and res.data else None
    except Exception:
        return None


def _bg_project_access(client, project_id: str, user: dict):
    """Load a project and the caller's access to it.

    Returns (project_or_None, is_member, can_manage). ``is_member`` is True when
    the user owns the project or has a project_members row; ``can_manage`` when
    the user may manage members (owner or same-org admin). Mirrors the checks in
    bg_project_detail so agent routes share one source of truth.
    """
    if client is None or not project_id or not user:
        return None, False, False
    try:
        pres = (
            client.table("projects")
            .select("id, name, description, location, owner_id, created_at")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        project = pres.data[0] if pres and pres.data else None
    except Exception:
        project = None
    if not project:
        return None, False, False
    try:
        mres = (
            client.table("project_members")
            .select("user_id")
            .eq("project_id", project_id)
            .execute()
        )
        members = mres.data or []
    except Exception:
        members = []
    is_owner = project.get("owner_id") == user.get("id")
    is_member = is_owner or any(m.get("user_id") == user.get("id") for m in members)
    can_manage = _bg_can_manage_members(client, project, user)
    return project, is_member, can_manage


def _bg_verify_and_register_agent(client, *, name: str, agent_url: str,
                                  agent_type: str, org_id: str,
                                  project_id: Optional[str], created_by: str):
    """Ping the discovery card and insert the agent row.

    Returns (agent_row_or_None, error_message). On a successful discovery ping
    the agent is stored as 'approved' with the cached card; otherwise it is
    stored 'pending' and the caller can retry the ping later.
    """
    base = _bg_normalize_agent_url(agent_url)
    ok, card, err = _bg_fetch_discovery_card(base)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    row = {
        "name": name,
        "type": agent_type,
        "org_id": org_id,
        "project_id": project_id,
        "created_by": created_by,
        "agent_url": base,
        "discovery_card": card if ok else None,
        "status": "approved" if ok else "pending",
        "approved_at": now if ok else None,
        "last_ping": now if ok else None,
    }
    try:
        res = client.table("agents").insert(row).execute()
        agent = res.data[0] if res and res.data else None
    except Exception as exc:
        return None, f"Could not save agent: {exc}"
    if not agent:
        return None, "Could not save agent. Please try again."
    if not ok:
        return agent, err
    return agent, ""


# ── Organization agent registry ──────────────────────────────────────────

def _bg_org_agents_page(user: dict, org: dict, member_role: str, agents: list,
                        notice: str = "") -> str:
    is_admin = (member_role or "").lower() == "admin"
    create_btn = ""
    modal = ""
    if is_admin:
        create_btn = (
            '<button class="btn primary sm" type="button" '
            "onclick=\"document.getElementById('agentModal').style.display='flex'\">"
            "+ Create Organization Agent</button>"
        )
        modal = (
            '<div id="agentModal" style="display:none;position:fixed;inset:0;z-index:100;'
            'background:rgba(0,0,0,.7);align-items:center;justify-content:center;padding:1rem">'
            '<div class="card" style="max-width:460px;width:100%">'
            "<h2>Create Organization Agent</h2>"
            '<p class="sub" style="margin-bottom:1rem">Register a persistent agent your '
            "firm operates. Build Guild verifies it by fetching its discovery card at "
            "<code>/.well-known/agent.json</code>.</p>"
            '<form method="post" action="/build-guild/org/agents/create">'
            '<label for="ag_name">Agent name</label>'
            '<input id="ag_name" name="name" type="text" required '
            'placeholder="e.g. Zero Engineering Agent">'
            '<label for="ag_url">Agent URL</label>'
            '<input id="ag_url" name="agent_url" type="url" required '
            'placeholder="https://your-agent.example.com">'
            '<div style="height:1.2rem"></div>'
            '<div class="row" style="justify-content:flex-end">'
            '<button class="btn sm" type="button" '
            "onclick=\"document.getElementById('agentModal').style.display='none'\">"
            "Cancel</button>"
            '<button class="btn primary sm" type="submit">Verify &amp; register</button>'
            "</div></form></div></div>"
        )

    rows = []
    for a in agents:
        card = a.get("discovery_card") or {}
        caps = _bg_agent_card_summary(card)
        last_ping = a.get("last_ping") or ""
        if last_ping:
            last_ping = last_ping.replace("T", " ")[:16]
        actions = (
            '<form method="post" '
            f'action="/build-guild/org/agents/{_bg_esc(a["id"])}/ping" style="display:inline;margin:0">'
            '<button class="btn sm" type="submit">Ping / Re-verify</button></form>'
        )
        if is_admin and (a.get("status") or "") != "offline":
            actions += (
                ' <form method="post" '
                f'action="/build-guild/org/agents/{_bg_esc(a["id"])}/deactivate" '
                "onsubmit=\"return confirm('Deactivate this agent? It will be marked offline.')\" "
                'style="display:inline;margin:0">'
                '<button class="btn danger sm" type="submit">Deactivate</button></form>'
            )
        last_ping_cell = _bg_esc(last_ping) or '<span class="sub">never</span>'
        caps_cell = _bg_esc(caps) or '<span class="sub">—</span>'
        agent_url_val = _bg_esc(a.get("agent_url") or "")
        rows.append(
            "<tr>"
            f"<td>{_bg_esc(a.get('name') or '—')}</td>"
            f'<td><a href="{agent_url_val}" target="_blank" '
            f'rel="noopener" style="word-break:break-all">{agent_url_val}</a></td>'
            f"<td>{_bg_agent_status_badge(a.get('status'))}</td>"
            f"<td>{last_ping_cell}</td>"
            f"<td>{caps_cell}</td>"
            f"<td>{actions}</td>"
            "</tr>"
        )
    if rows:
        table = (
            "<table><thead><tr><th>Name</th><th>URL</th><th>Status</th>"
            "<th>Last ping</th><th>Capabilities</th><th>Actions</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
    else:
        table = (
            '<div class="empty">No organization agents yet.'
            + ("<br>Click “Create Organization Agent” to register your firm’s agent."
               if is_admin else "<br>An organization admin can register your firm’s agent.")
            + "</div>"
        )

    body = (
        '<div class="wrap" style="padding-top:1.6rem;padding-bottom:4rem">'
        '<a class="backlink" href="/build-guild/dashboard">&larr; Back to dashboard</a>'
        f"{notice}"
        '<div class="pagehead" style="margin-top:1rem">'
        f'<div><h1>Organization Agents</h1>'
        f'<p class="sub" style="margin-bottom:0">Persistent agents operated by '
        f'{_bg_esc(org.get("name") or "your organization")}</p></div>'
        f"{create_btn}"
        "</div>"
        f"{table}"
        f"{modal}"
        "</div>"
    )
    return _bg_shell("Organization Agents", body, user)


@app.get("/build-guild/org/agents", response_class=HTMLResponse)
async def bg_org_agents(bg_session: Optional[str] = Cookie(default=None),
                        notice: Optional[str] = None,
                        err: Optional[str] = None):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    membership = _bg_get_membership(client, user["id"])
    if not membership:
        return RedirectResponse("/build-guild/org", status_code=303)
    org = membership["org"]
    agents = _bg_org_agents(client, org["id"], agent_type="company")
    banner = ""
    if notice:
        banner = f'<div class="msg ok">{_bg_esc(notice)}</div>'
    elif err:
        banner = f'<div class="msg err">{_bg_esc(err)}</div>'
    return HTMLResponse(_bg_org_agents_page(
        user, org, membership["member_role"], agents, banner))


@app.post("/build-guild/org/agents/create", response_class=HTMLResponse)
async def bg_org_agents_create(request: Request,
                               bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return RedirectResponse("/build-guild/org/agents?err=Database+not+configured",
                                status_code=303)
    membership = _bg_get_membership(client, user["id"])
    if not membership:
        return RedirectResponse("/build-guild/org", status_code=303)
    if (membership["member_role"] or "").lower() != "admin":
        return RedirectResponse(
            "/build-guild/org/agents?err=Only+an+organization+admin+can+create+company+agents",
            status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    agent_url = (form.get("agent_url") or "").strip()
    from urllib.parse import quote_plus
    if not name or not agent_url:
        return RedirectResponse(
            "/build-guild/org/agents?err=" + quote_plus("Name and agent URL are required."),
            status_code=303)

    agent, err = _bg_verify_and_register_agent(
        client, name=name, agent_url=agent_url, agent_type="company",
        org_id=membership["org"]["id"], project_id=None, created_by=user["id"])
    if agent is None:
        return RedirectResponse("/build-guild/org/agents?err=" + quote_plus(err),
                                status_code=303)
    if err:
        msg = ("Agent saved as pending — discovery verification failed: " + err
               + " Use Ping / Re-verify once it is reachable.")
        return RedirectResponse("/build-guild/org/agents?err=" + quote_plus(msg),
                                status_code=303)
    return RedirectResponse(
        "/build-guild/org/agents?notice=" + quote_plus(
            f"Agent “{name}” verified and approved."),
        status_code=303)


@app.post("/build-guild/org/agents/{agent_id}/ping")
async def bg_org_agent_ping(agent_id: str,
                            bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    membership = _bg_get_membership(client, user["id"]) if client else None
    agent = _bg_get_agent(client, agent_id) if client else None
    if not membership or not agent or agent.get("org_id") != membership["org"]["id"]:
        return RedirectResponse("/build-guild/org/agents?err=Agent+not+found",
                                status_code=303)
    ok, card, err = _bg_fetch_discovery_card(agent.get("agent_url") or "")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    update = {"last_ping": now}
    if ok:
        update.update({"status": "approved", "discovery_card": card,
                       "approved_at": agent.get("approved_at") or now})
        msg = "notice=" + quote_plus("Agent re-verified — reachable and approved.")
    else:
        # Only downgrade an approved agent to offline; keep pending as pending.
        update["status"] = "offline" if agent.get("status") == "approved" else "pending"
        msg = "err=" + quote_plus("Re-verify failed: " + err)
    try:
        client.table("agents").update(update).eq("id", agent_id).execute()
    except Exception as exc:
        msg = "err=" + quote_plus(f"Could not update agent: {exc}")
    return RedirectResponse(f"/build-guild/org/agents?{msg}", status_code=303)


@app.post("/build-guild/org/agents/{agent_id}/deactivate")
async def bg_org_agent_deactivate(agent_id: str,
                                  bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    membership = _bg_get_membership(client, user["id"]) if client else None
    agent = _bg_get_agent(client, agent_id) if client else None
    if not membership or not agent or agent.get("org_id") != membership["org"]["id"]:
        return RedirectResponse("/build-guild/org/agents?err=Agent+not+found",
                                status_code=303)
    if (membership["member_role"] or "").lower() != "admin":
        return RedirectResponse(
            "/build-guild/org/agents?err=" + quote_plus(
                "Only an organization admin can deactivate company agents."),
            status_code=303)
    try:
        client.table("agents").update({"status": "offline"}).eq("id", agent_id).execute()
    except Exception as exc:
        return RedirectResponse(
            "/build-guild/org/agents?err=" + quote_plus(f"Could not deactivate: {exc}"),
            status_code=303)
    return RedirectResponse(
        "/build-guild/org/agents?notice=" + quote_plus("Agent deactivated (offline)."),
        status_code=303)


# ── Organization MCP connection strings ──────────────────────────────────
#
# Each organization can register multiple MCP connection URLs — the URL a user
# plugs into their LLM connector so it can send queries to Build Guild on
# behalf of the org (an outbound sender-identity channel, distinct from the
# inbound persistent-agent registry above). Each connection is named/described
# (e.g. "Procurement", "Safety", "Project Management"). Any member of the org
# may manage them; agents acting on behalf of the org consume them at runtime.

_MCP_CONN_COLS = ("id, org_id, name, description, url, token, created_by, "
                  "created_at, updated_at")


def _bg_org_mcp_connections(client, org_id: str) -> list:
    """Fetch all MCP connections for an org, newest first."""
    if client is None or not org_id:
        return []
    try:
        res = (
            client.table("mcp_connections")
            .select(_MCP_CONN_COLS)
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        _guild_logger.warning("Load MCP connections for org %s failed: %s",
                              org_id, exc)
        return []


def _bg_get_mcp_connection(client, conn_id: str) -> Optional[dict]:
    if client is None or not conn_id:
        return None
    try:
        res = (
            client.table("mcp_connections")
            .select(_MCP_CONN_COLS)
            .eq("id", conn_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res and res.data else None
    except Exception:
        return None


def _bg_org_mcp_page(user: dict, org: dict, member_role: str, connections: list,
                     edit_conn: Optional[dict] = None, notice: str = "") -> str:
    """Render the org MCP connections management page.

    Any org member may add / edit / delete, so the controls are always shown.
    ``edit_conn`` pre-opens the edit modal for that connection.
    """
    create_btn = (
        '<button class="btn primary sm" type="button" '
        "onclick=\"document.getElementById('mcpAddModal').style.display='flex'\">"
        "+ Add MCP Connection</button>"
    )
    add_modal = (
        '<div id="mcpAddModal" style="display:none;position:fixed;inset:0;z-index:100;'
        'background:rgba(0,0,0,.7);align-items:center;justify-content:center;padding:1rem">'
        '<div class="card" style="max-width:460px;width:100%">'
        "<h2>Add MCP Connection</h2>"
        '<p class="sub" style="margin-bottom:1rem">Create an MCP connection your team '
        "plugs into an LLM connector to query Build Guild on behalf of this "
        "organization. Just give it a name (e.g. Procurement, Safety, Project "
        "Management) &mdash; Build Guild generates a unique connection URL for you.</p>"
        '<form method="post" action="/build-guild/org/mcp-connections/create">'
        '<label for="mcp_name">Name</label>'
        '<input id="mcp_name" name="name" type="text" required '
        'placeholder="e.g. Procurement">'
        '<label for="mcp_desc">Description <span class="sub">(optional)</span></label>'
        '<input id="mcp_desc" name="description" type="text" '
        'placeholder="What this connection is for">'
        '<div style="height:1.2rem"></div>'
        '<div class="row" style="justify-content:flex-end">'
        '<button class="btn sm" type="button" '
        "onclick=\"document.getElementById('mcpAddModal').style.display='none'\">"
        "Cancel</button>"
        '<button class="btn primary sm" type="submit">Save connection</button>'
        "</div></form></div></div>"
    )

    # Per-row edit modals (kept simple, one per connection).
    edit_modals = []
    rows = []
    for c in connections:
        cid = _bg_esc(c["id"])
        name = _bg_esc(c.get("name") or "—")
        desc = _bg_esc(c.get("description") or "")
        desc_cell = desc or '<span class="sub">—</span>'
        url_raw = c.get("url") or ""
        url_val = _bg_esc(url_raw)
        # JS string-literal safe copy value.
        url_js = (url_raw.replace("\\", "\\\\").replace("'", "\\'")
                  .replace("\n", "").replace("\r", ""))
        modal_id = f"mcpEdit_{cid}"
        copy_btn = (
            f'<button class="btn sm" type="button" '
            f"onclick=\"navigator.clipboard.writeText('{url_js}');"
            "this.textContent='Copied!';"
            "setTimeout(function(){this.textContent='Copy';}.bind(this),1500)\">"
            "Copy</button>"
        )
        url_cell = (
            '<div style="display:flex;gap:.4rem;align-items:center">'
            f'<a href="{url_val}" target="_blank" rel="noopener" '
            f'style="word-break:break-all">{url_val}</a>'
            f"{copy_btn}</div>"
        )
        actions = (
            f'<button class="btn sm" type="button" '
            f"onclick=\"document.getElementById('{modal_id}').style.display='flex'\">"
            "Edit</button> "
            '<form method="post" '
            f'action="/build-guild/org/mcp-connections/{cid}/delete" '
            "onsubmit=\"return confirm('Delete this MCP connection? This cannot be undone.')\" "
            'style="display:inline;margin:0">'
            '<button class="btn danger sm" type="submit">Delete</button></form>'
        )
        created = (c.get("created_at") or "").replace("T", " ")[:16]
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td>{desc_cell}</td>"
            f"<td>{url_cell}</td>"
            f'<td>{_bg_esc(created) or "&mdash;"}</td>'
            f"<td>{actions}</td>"
            "</tr>"
        )
        edit_modals.append(
            f'<div id="{modal_id}" style="display:none;position:fixed;inset:0;z-index:100;'
            'background:rgba(0,0,0,.7);align-items:center;justify-content:center;padding:1rem">'
            '<div class="card" style="max-width:460px;width:100%">'
            "<h2>Edit MCP Connection</h2>"
            f'<form method="post" action="/build-guild/org/mcp-connections/{cid}/edit">'
            '<label>Name</label>'
            f'<input name="name" type="text" required value="{name}">'
            '<label>Description <span class="sub">(optional)</span></label>'
            f'<input name="description" type="text" value="{desc}">'
            '<label>Connection URL <span class="sub">(generated &mdash; read only)</span></label>'
            f'<input type="text" value="{url_val}" readonly '
            'style="background:rgba(255,255,255,.05);color:#9aa4b2;cursor:not-allowed">'
            '<div style="height:1.2rem"></div>'
            '<div class="row" style="justify-content:flex-end">'
            '<button class="btn sm" type="button" '
            f"onclick=\"document.getElementById('{modal_id}').style.display='none'\">"
            "Cancel</button>"
            '<button class="btn primary sm" type="submit">Save changes</button>'
            "</div></form></div></div>"
        )

    if rows:
        table = (
            "<table><thead><tr><th>Name</th><th>Description</th><th>URL</th>"
            "<th>Created</th><th>Actions</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
    else:
        table = (
            '<div class="empty">No MCP connections yet.'
            "<br>Click &ldquo;Add MCP Connection&rdquo; to register your first one."
            "</div>"
        )

    # Auto-open an edit modal if requested via ?edit=<id>.
    autoscript = ""
    if edit_conn:
        autoscript = (
            "<script>document.getElementById('mcpEdit_"
            f"{_bg_esc(edit_conn['id'])}').style.display='flex';</script>"
        )

    body = (
        '<div class="wrap" style="padding-top:1.6rem;padding-bottom:4rem">'
        '<a class="backlink" href="/build-guild/dashboard">&larr; Back to dashboard</a>'
        f"{notice}"
        '<div class="pagehead" style="margin-top:1rem">'
        f'<div><h1>MCP Connections</h1>'
        f'<p class="sub" style="margin-bottom:0">Outbound MCP connection URLs for '
        f'{_bg_esc(org.get("name") or "your organization")} — plug these into an LLM '
        'connector to query Build Guild on behalf of the org</p></div>'
        f"{create_btn}"
        "</div>"
        f"{table}"
        f"{add_modal}"
        f"{''.join(edit_modals)}"
        f"{autoscript}"
        "</div>"
    )
    return _bg_shell("MCP Connections", body, user)


@app.get("/build-guild/org/mcp-connections", response_class=HTMLResponse)
async def bg_org_mcp_connections(bg_session: Optional[str] = Cookie(default=None),
                                 edit: Optional[str] = None,
                                 notice: Optional[str] = None,
                                 err: Optional[str] = None):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    membership = _bg_get_membership(client, user["id"]) if client else None
    if not membership:
        return RedirectResponse("/build-guild/org", status_code=303)
    org = membership["org"]
    connections = _bg_org_mcp_connections(client, org["id"])
    edit_conn = None
    if edit:
        edit_conn = next((c for c in connections if str(c.get("id")) == edit), None)
    banner = ""
    if notice:
        banner = f'<div class="msg ok">{_bg_esc(notice)}</div>'
    elif err:
        banner = f'<div class="msg err">{_bg_esc(err)}</div>'
    return HTMLResponse(_bg_org_mcp_page(
        user, org, membership["member_role"], connections, edit_conn, banner))


@app.post("/build-guild/org/mcp-connections/create", response_class=HTMLResponse)
async def bg_org_mcp_create(request: Request,
                            bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    if client is None:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err=Database+not+configured",
            status_code=303)
    membership = _bg_get_membership(client, user["id"])
    if not membership:
        return RedirectResponse("/build-guild/org", status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    description = (form.get("description") or "").strip()
    if not name:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err="
            + quote_plus("A name is required."),
            status_code=303)

    # Build Guild mints a unique, identity-bearing URL for each connection.
    token = secrets_mod.token_urlsafe(24)
    base = _bg_base_url(request)
    url = f"{base}/build-guild/mcp/{token}"
    row = {
        "org_id": membership["org"]["id"],
        "name": name,
        "description": description or None,
        "url": url,
        "token": token,
        "created_by": user["id"],
    }
    try:
        client.table("mcp_connections").insert(row).execute()
    except Exception as exc:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err="
            + quote_plus(f"Could not save connection: {exc}"),
            status_code=303)
    return RedirectResponse(
        "/build-guild/org/mcp-connections?notice="
        + quote_plus(f"MCP connection “{name}” added."),
        status_code=303)


@app.post("/build-guild/org/mcp-connections/{conn_id}/edit",
          response_class=HTMLResponse)
async def bg_org_mcp_edit(conn_id: str, request: Request,
                          bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    membership = _bg_get_membership(client, user["id"]) if client else None
    conn = _bg_get_mcp_connection(client, conn_id) if client else None
    if not membership or not conn or conn.get("org_id") != membership["org"]["id"]:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err=Connection+not+found",
            status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    description = (form.get("description") or "").strip()
    if not name:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err="
            + quote_plus("A name is required."),
            status_code=303)

    # The connection URL / token are immutable so existing connectors keep
    # working; only the label and description can be edited.
    update = {"name": name, "description": description or None}
    try:
        client.table("mcp_connections").update(update).eq("id", conn_id).execute()
    except Exception as exc:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err="
            + quote_plus(f"Could not update connection: {exc}"),
            status_code=303)
    return RedirectResponse(
        "/build-guild/org/mcp-connections?notice="
        + quote_plus(f"MCP connection “{name}” updated."),
        status_code=303)


@app.post("/build-guild/org/mcp-connections/{conn_id}/delete",
          response_class=HTMLResponse)
async def bg_org_mcp_delete(conn_id: str,
                            bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    membership = _bg_get_membership(client, user["id"]) if client else None
    conn = _bg_get_mcp_connection(client, conn_id) if client else None
    if not membership or not conn or conn.get("org_id") != membership["org"]["id"]:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err=Connection+not+found",
            status_code=303)
    try:
        client.table("mcp_connections").delete().eq("id", conn_id).execute()
    except Exception as exc:
        return RedirectResponse(
            "/build-guild/org/mcp-connections?err="
            + quote_plus(f"Could not delete connection: {exc}"),
            status_code=303)
    return RedirectResponse(
        "/build-guild/org/mcp-connections?notice="
        + quote_plus("MCP connection deleted."),
        status_code=303)


@app.get("/build-guild/org/{org_id}/mcp-connections.json")
async def bg_org_mcp_connections_json(org_id: str,
                                      bg_session: Optional[str] = Cookie(default=None)):
    """Machine-readable list of an org's MCP connections.

    Consumed by agents acting on behalf of the org (and by org members). Access
    is limited to authenticated members of the requested organization, mirroring
    the server-side authorization used throughout the app.
    """
    user = _bg_get_current_user(bg_session)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    client = get_supabase()
    membership = _bg_get_membership(client, user["id"]) if client else None
    if not membership or membership["org"]["id"] != org_id:
        return JSONResponse({"error": "not found"}, status_code=404)
    connections = _bg_org_mcp_connections(client, org_id)
    return JSONResponse({
        "org_id": org_id,
        "connections": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "description": c.get("description"),
                "url": c.get("url"),
                "created_at": c.get("created_at"),
                "updated_at": c.get("updated_at"),
            }
            for c in connections
        ],
    })


@app.get("/build-guild/mcp/{token}")
async def bg_mcp_resolve(token: str):
    """Resolve a minted MCP connection URL to the org identity it represents.

    This is the public endpoint that each generated connection URL points at.
    An LLM connector hits it to discover which organization (and which named
    connection) the caller is acting on behalf of. Returns a compact identity
    document, or 404 if the token is unknown.
    """
    client = get_supabase()
    if client is None:
        return JSONResponse({"ok": False, "error": "unavailable"}, status_code=503)
    conn = None
    try:
        res = (
            client.table("mcp_connections")
            .select(_MCP_CONN_COLS)
            .eq("token", token)
            .limit(1)
            .execute()
        )
        conn = res.data[0] if res and res.data else None
    except Exception as exc:
        _guild_logger.warning("MCP token resolve failed: %s", exc)
        return JSONResponse({"ok": False, "error": "error"}, status_code=500)
    if not conn:
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
    org = None
    try:
        ores = (
            client.table("organizations")
            .select("id, name")
            .eq("id", conn.get("org_id"))
            .limit(1)
            .execute()
        )
        org = ores.data[0] if ores and ores.data else None
    except Exception:
        org = None
    return JSONResponse({
        "ok": True,
        "org_id": conn.get("org_id"),
        "org_name": (org or {}).get("name"),
        "connection_id": conn.get("id"),
        "connection_name": conn.get("name"),
        "connection_description": conn.get("description"),
    })


# ── Project agents: create / ping / deactivate / message thread ──────────

@app.post("/build-guild/project/{project_id}/agents/create")
async def bg_project_agent_create(project_id: str, request: Request,
                                  bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    if client is None:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Database+not+configured",
                                status_code=303)
    project, is_member, _ = _bg_project_access(client, project_id, user)
    if not project or not is_member:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=" + quote_plus("You are not a member of this project."),
            status_code=303)
    # Resolve the org that owns this project (via the project owner's membership).
    owner_mem = _bg_get_membership(client, project.get("owner_id"))
    org_id = (owner_mem or {}).get("org", {}).get("id")
    if not org_id:
        # Fall back to the acting member's org.
        acting = _bg_get_membership(client, user["id"])
        org_id = (acting or {}).get("org", {}).get("id")
    if not org_id:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=" + quote_plus("No organization found for this project."),
            status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    agent_url = (form.get("agent_url") or "").strip()
    if not name or not agent_url:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=" + quote_plus("Name and agent URL are required."),
            status_code=303)

    agent, err = _bg_verify_and_register_agent(
        client, name=name, agent_url=agent_url, agent_type="project",
        org_id=org_id, project_id=project_id, created_by=user["id"])
    if agent is None:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=" + quote_plus(err), status_code=303)
    if err:
        msg = ("Project agent saved as pending — discovery verification failed: " + err)
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=" + quote_plus(msg), status_code=303)
    return RedirectResponse(
        f"/build-guild/project/{project_id}?agent_notice=" + quote_plus(
            f"Project agent “{name}” verified and approved."),
        status_code=303)


@app.post("/build-guild/project/{project_id}/agents/{agent_id}/ping")
async def bg_project_agent_ping(project_id: str, agent_id: str,
                                bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    project, is_member, _ = _bg_project_access(client, project_id, user) if client else (None, False, False)
    agent = _bg_get_agent(client, agent_id) if client else None
    if not project or not is_member or not agent:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Agent+not+found",
                                status_code=303)
    ok, card, err = _bg_fetch_discovery_card(agent.get("agent_url") or "")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    update = {"last_ping": now}
    if ok:
        update.update({"status": "approved", "discovery_card": card,
                       "approved_at": agent.get("approved_at") or now})
        msg = "agent_notice=" + quote_plus("Agent re-verified — reachable and approved.")
    else:
        update["status"] = "offline" if agent.get("status") == "approved" else "pending"
        msg = "err=" + quote_plus("Re-verify failed: " + err)
    try:
        client.table("agents").update(update).eq("id", agent_id).execute()
    except Exception as exc:
        msg = "err=" + quote_plus(f"Could not update agent: {exc}")
    return RedirectResponse(f"/build-guild/project/{project_id}?{msg}", status_code=303)


@app.post("/build-guild/project/{project_id}/agents/{agent_id}/deactivate")
async def bg_project_agent_deactivate(project_id: str, agent_id: str,
                                      bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    project, is_member, _ = _bg_project_access(client, project_id, user) if client else (None, False, False)
    agent = _bg_get_agent(client, agent_id) if client else None
    # Only allow deactivating project agents that belong to this project.
    if (not project or not is_member or not agent
            or agent.get("type") != "project"
            or agent.get("project_id") != project_id):
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Agent+not+found",
                                status_code=303)
    try:
        client.table("agents").update({"status": "offline"}).eq("id", agent_id).execute()
    except Exception as exc:
        return RedirectResponse(
            f"/build-guild/project/{project_id}?err=" + quote_plus(f"Could not deactivate: {exc}"),
            status_code=303)
    return RedirectResponse(
        f"/build-guild/project/{project_id}?agent_notice=" + quote_plus("Agent deactivated (offline)."),
        status_code=303)


@app.get("/build-guild/project/{project_id}/agents/{agent_id}/thread",
         response_class=HTMLResponse)
async def bg_agent_thread(project_id: str, agent_id: str,
                          err: Optional[str] = None,
                          bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    if client is None:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Database+not+configured",
                                status_code=303)
    project, is_member, _ = _bg_project_access(client, project_id, user)
    agent = _bg_get_agent(client, agent_id)
    if not project or not is_member or not agent:
        return HTMLResponse(_bg_shell(
            "Not found",
            '<div class="wrap" style="padding-top:3rem"><div class="card">'
            "<h1>Agent not found</h1>"
            f'<a class="btn primary" href="/build-guild/project/{_bg_esc(project_id)}">Back to project</a>'
            "</div></div>", user), status_code=404)
    # A company agent must belong to the same org; a project agent to this project.
    membership = _bg_get_membership(client, user["id"])
    caller_org = (membership or {}).get("org", {}).get("id")
    if agent.get("type") == "project" and agent.get("project_id") != project_id:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Agent+not+found",
                                status_code=303)
    if agent.get("type") == "company" and agent.get("org_id") != caller_org:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Agent+not+found",
                                status_code=303)

    # Load thread history for this agent within this project.
    try:
        mres = (
            client.table("agent_messages")
            .select("id, sender, from_firm, body, conversation_id, created_at")
            .eq("agent_id", agent_id)
            .eq("project_id", project_id)
            .order("created_at", desc=False)
            .execute()
        )
        msgs = mres.data or []
    except Exception:
        msgs = []

    bubbles = []
    for m in msgs:
        is_user = (m.get("sender") or "") == "user"
        align = "flex-end" if is_user else "flex-start"
        bg = "var(--panel-hi)" if is_user else "var(--panel)"
        who = "You" if is_user else (m.get("from_firm") or agent.get("name") or "Agent")
        bubbles.append(
            f'<div style="display:flex;justify-content:{align};margin:.4rem 0">'
            f'<div style="max-width:80%;background:{bg};border:1px solid var(--border);'
            f'border-radius:12px;padding:.6rem .85rem">'
            f'<div style="font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;'
            f'color:var(--faint);margin-bottom:.2rem">{_bg_esc(who)}</div>'
            f'<div style="white-space:pre-wrap">{_bg_esc(m.get("body") or "")}</div>'
            "</div></div>"
        )
    thread_html = ("".join(bubbles) if bubbles
                   else '<p class="sub">No messages yet. Send the first message below.</p>')

    notice = f'<div class="msg err">{_bg_esc(err)}</div>' if err else ""
    card = agent.get("discovery_card") or {}
    caps = _bg_agent_card_summary(card)
    caps_html = (f'<p class="sub" style="margin-top:.3rem">Capabilities: {_bg_esc(caps)}</p>'
                 if caps else "")
    body = (
        '<div class="wrap narrow" style="padding-top:1.6rem;padding-bottom:4rem;max-width:640px">'
        f'<a class="backlink" href="/build-guild/project/{_bg_esc(project_id)}">&larr; Back to project</a>'
        f"{notice}"
        '<div class="pagehead" style="margin-top:1rem">'
        f'<div><h1 style="font-size:1.35rem">{_bg_esc(agent.get("name") or "Agent")} '
        f'{_bg_agent_status_badge(agent.get("status"))}</h1>'
        f'<p class="sub" style="margin-bottom:0">{_bg_esc(agent.get("type","").title())} agent · '
        f'{_bg_esc(agent.get("agent_url") or "")}</p>{caps_html}</div></div>'
        '<div class="card" style="margin-top:1rem">'
        f'<div style="max-height:52vh;overflow-y:auto;margin-bottom:1rem">{thread_html}</div>'
        f'<form method="post" action="/build-guild/project/{_bg_esc(project_id)}/agents/{_bg_esc(agent_id)}/message">'
        '<label for="msg">Message</label>'
        '<textarea id="msg" name="message" required placeholder="Type a message to this agent…"></textarea>'
        '<div style="height:.9rem"></div>'
        '<button class="btn primary" type="submit">Send</button>'
        "</form></div></div>"
    )
    return HTMLResponse(_bg_shell(f"{agent.get('name') or 'Agent'} — thread", body, user))


@app.post("/build-guild/project/{project_id}/agents/{agent_id}/message")
async def bg_agent_message(project_id: str, agent_id: str, request: Request,
                           bg_session: Optional[str] = Cookie(default=None)):
    user = _bg_get_current_user(bg_session)
    if not user:
        return RedirectResponse("/build-guild/login", status_code=303)
    client = get_supabase()
    from urllib.parse import quote_plus
    thread_url = f"/build-guild/project/{project_id}/agents/{agent_id}/thread"
    if client is None:
        return RedirectResponse(thread_url + "?err=Database+not+configured", status_code=303)
    project, is_member, _ = _bg_project_access(client, project_id, user)
    agent = _bg_get_agent(client, agent_id)
    membership = _bg_get_membership(client, user["id"])
    caller_org = (membership or {}).get("org", {}).get("id")
    caller_firm = (membership or {}).get("org", {}).get("name") or "Build Guild"
    if not project or not is_member or not agent:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Agent+not+found",
                                status_code=303)
    if agent.get("type") == "project" and agent.get("project_id") != project_id:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Agent+not+found",
                                status_code=303)
    if agent.get("type") == "company" and agent.get("org_id") != caller_org:
        return RedirectResponse(f"/build-guild/project/{project_id}?err=Agent+not+found",
                                status_code=303)

    form = await request.form()
    message = (form.get("message") or "").strip()
    if not message:
        return RedirectResponse(thread_url, status_code=303)

    # Find an existing conversation_id for this thread to continue it.
    conv_id = None
    try:
        prev = (
            client.table("agent_messages")
            .select("conversation_id")
            .eq("agent_id", agent_id)
            .eq("project_id", project_id)
            .not_.is_("conversation_id", None)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if prev and prev.data:
            conv_id = prev.data[0].get("conversation_id")
    except Exception:
        conv_id = None

    # Persist the user's message first.
    try:
        client.table("agent_messages").insert({
            "agent_id": agent_id,
            "project_id": project_id,
            "conversation_id": conv_id,
            "sender": "user",
            "from_firm": caller_firm,
            "body": message,
            "created_by": user["id"],
        }).execute()
    except Exception as exc:
        _guild_logger.warning("Persist user agent-message failed: %s", exc)

    payload = {
        "from_agent": f"Build Guild ({user.get('email') or 'member'})",
        "from_firm": caller_firm,
        "message": message,
        "metadata": {"project_id": project_id, "project_name": project.get("name")},
    }
    if conv_id:
        payload["conversation_id"] = conv_id

    ok, data, err = _bg_relay_agent_message(agent.get("agent_url") or "", payload)
    if not ok:
        # Mark unreachable agent offline (best-effort) and report the error.
        try:
            client.table("agents").update({"status": "offline"}).eq("id", agent_id).execute()
        except Exception:
            pass
        return RedirectResponse(thread_url + "?err=" + quote_plus("Agent did not reply: " + err),
                                status_code=303)

    reply = data.get("reply") or data.get("message") or "(no reply text)"
    new_conv = data.get("conversation_id") or conv_id
    reply_firm = data.get("from_firm") or agent.get("name") or "Agent"
    try:
        client.table("agent_messages").insert({
            "agent_id": agent_id,
            "project_id": project_id,
            "conversation_id": new_conv,
            "sender": "agent",
            "from_firm": reply_firm,
            "body": str(reply),
            "created_by": user["id"],
        }).execute()
        # Backfill conversation_id on the user's row if it was newly assigned.
        if new_conv and not conv_id:
            client.table("agent_messages").update({"conversation_id": new_conv}) \
                .eq("agent_id", agent_id).eq("project_id", project_id) \
                .is_("conversation_id", None).execute()
    except Exception as exc:
        _guild_logger.warning("Persist agent reply failed: %s", exc)

    return RedirectResponse(thread_url, status_code=303)


# ---------------------------------------------------------------------------
# Build Guild registration -- agent-callable, issues a signed JWT credential
# ---------------------------------------------------------------------------

_guild_logger = logging.getLogger("build_guild")

VALID_GUILD_ROLES = {"Architect", "Engineer", "Contractor", "Vendor", "Owner"}

_JWT_FALLBACK_SECRET = "build-guild-dev-secret-change-in-production"


def _guild_jwt_secret() -> str:
    """Return the JWT signing secret, warning if the env var is not set."""
    secret = os.environ.get("GUILD_JWT_SECRET")
    if not secret:
        _guild_logger.warning(
            "GUILD_JWT_SECRET is not set; using insecure development fallback. "
            "Set GUILD_JWT_SECRET in the environment for production."
        )
        return _JWT_FALLBACK_SECRET
    return secret


# ---------------------------------------------------------------------------
# Shared credential + directory helpers (used by MCP find_agents and A2A)
# ---------------------------------------------------------------------------

def _guild_verify_jwt(token: Any) -> dict:
    """Decode/validate a project_credential JWT.

    Returns {"valid": True, "claims": {...}} on success, or
    {"valid": False, "error": "..."} on failure.
    """
    if not token or not isinstance(token, str) or not token.strip():
        return {"valid": False, "error": "No credential token provided."}
    try:
        claims = jwt.decode(token.strip(), _guild_jwt_secret(), algorithms=["HS256"])
    except Exception as exc:  # ExpiredSignatureError, JWTError, etc.
        return {"valid": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"valid": True, "claims": claims}


def _extract_bearer(auth_header: Any) -> Optional[str]:
    """Pull the token out of an 'Authorization: Bearer <token>' header value."""
    if not auth_header or not isinstance(auth_header, str):
        return None
    parts = auth_header.strip().split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    # Also tolerate a bare token being passed.
    return auth_header.strip() or None


def _query_guild_directory(role=None, a2a_only=False, search=None) -> dict:
    """Query guild_members for the public directory.

    Returns {"ok": True, "members": [...]} or {"ok": False, "error": "..."}.
    Never exposes project_credential or internal fields.
    """
    client = get_supabase()
    if client is None:
        return {
            "ok": False,
            "error": "Supabase is not configured (SUPABASE_URL / SUPABASE_ANON_KEY missing).",
        }

    # Select only safe, public columns. a2a_endpoint may not exist yet -- if the
    # select errors on it, retry without it.
    cols_with_a2a = "org_name, role, contact_name, tier, created_at, a2a_endpoint"
    cols_basic = "org_name, role, contact_name, tier, created_at"

    def _run(select_cols, include_a2a_filter):
        q = client.table("guild_members").select(select_cols)
        if role:
            q = q.eq("role", role)
        if search and isinstance(search, str) and search.strip():
            escaped = search.strip().replace("%", r"\%").replace("_", r"\_")
            q = q.ilike("org_name", f"%{escaped}%")
        if include_a2a_filter and a2a_only:
            q = q.not_.is_("a2a_endpoint", "null")
        return q.execute()

    try:
        resp = _run(cols_with_a2a, True)
        rows = getattr(resp, "data", None) or []
    except Exception as exc:
        # a2a_endpoint column likely not provisioned -- fall back to basic cols.
        _guild_logger.warning("Directory query with a2a_endpoint failed (%s); "
                              "falling back to basic columns.", exc)
        try:
            resp = _run(cols_basic, False)
            rows = getattr(resp, "data", None) or []
            if a2a_only:
                # Column doesn't exist -> no members can have an endpoint.
                rows = []
        except Exception as exc2:
            return {"ok": False, "error": f"{type(exc2).__name__}: {exc2}"}

    members = []
    for r in rows:
        m = {
            "org_name": r.get("org_name"),
            "role": r.get("role"),
            "contact_name": r.get("contact_name"),
            "tier": r.get("tier"),
            "created_at": r.get("created_at"),
        }
        if r.get("a2a_endpoint"):
            m["a2a_endpoint"] = r.get("a2a_endpoint")
        members.append(m)
    return {"ok": True, "members": members}


def find_agents_tool(project_credential: Any, role: Any = None,
                     a2a_only: Any = None, search: Any = None) -> dict:
    """MCP tool: search the Build Guild member directory (requires JWT)."""
    verify = _guild_verify_jwt(project_credential)
    if not verify["valid"]:
        return _tool_text(
            "Directory access denied — invalid or missing project_credential. "
            f"({verify['error']}) Register with build_guild_register to obtain one.",
            is_error=True,
        )

    if role and role not in VALID_GUILD_ROLES:
        return _tool_text(
            f"Invalid role '{role}'. Must be one of: "
            + ", ".join(sorted(VALID_GUILD_ROLES)) + ".",
            is_error=True,
        )

    result = _query_guild_directory(
        role=role, a2a_only=bool(a2a_only), search=search
    )
    if not result["ok"]:
        return _tool_text(f"Directory query failed: {result['error']}", is_error=True)

    members = result["members"]
    caller = verify["claims"].get("org", "your organization")
    if not members:
        return _tool_text(
            f"No Build Guild members matched your query"
            + (f" (role={role})" if role else "")
            + (" with A2A endpoints" if a2a_only else "")
            + (f" matching '{search}'" if search else "")
            + ".",
            is_error=False,
        )

    lines = [
        f"Build Guild member directory — {len(members)} result(s)"
        f" (query by {caller}):",
        "",
    ]
    for i, m in enumerate(members, 1):
        line = f"{i}. {m.get('org_name')} — {m.get('role')} (tier: {m.get('tier')})"
        if m.get("a2a_endpoint"):
            line += f"\n   A2A endpoint: {m['a2a_endpoint']}"
        lines.append(line)
    lines.append("")
    lines.append(json.dumps({"members": members}))
    return _tool_text("\n".join(lines), is_error=False)


@app.post("/build-guild/register", status_code=201)
async def build_guild_register(request: Request):
    """Agent-callable registration for the Build Guild.

    Accepts a JSON body, records the member in Supabase, signs a 365-day JWT
    credential, and returns it. Fully completable from within an LLM session.
    """
    # --- Parse body ---
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_json",
                "message": "Request body must be valid JSON.",
            },
        )

    if not isinstance(body, dict):
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_body",
                "message": "Request body must be a JSON object.",
            },
        )

    org_name = (body.get("org_name") or "").strip() if isinstance(body.get("org_name"), str) else body.get("org_name")
    role = (body.get("role") or "").strip() if isinstance(body.get("role"), str) else body.get("role")
    contact_name = (body.get("contact_name") or "").strip() if isinstance(body.get("contact_name"), str) else body.get("contact_name")
    contact_email = (body.get("contact_email") or "").strip() if isinstance(body.get("contact_email"), str) else body.get("contact_email")
    a2a_endpoint = (body.get("a2a_endpoint") or "").strip() if isinstance(body.get("a2a_endpoint"), str) else body.get("a2a_endpoint")

    # --- Validate required fields ---
    missing = [
        field
        for field, value in (
            ("org_name", org_name),
            ("role", role),
            ("contact_name", contact_name),
            ("contact_email", contact_email),
        )
        if not value
    ]
    if missing:
        return JSONResponse(
            status_code=422,
            content={
                "error": "missing_fields",
                "message": (
                    "Missing required field(s): "
                    + ", ".join(missing)
                    + ". All of org_name, role, contact_name, contact_email are required."
                ),
            },
        )

    # --- Validate role ---
    if role not in VALID_GUILD_ROLES:
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_role",
                "message": (
                    f"Invalid role '{role}'. Must be one of: "
                    + ", ".join(sorted(VALID_GUILD_ROLES))
                    + "."
                ),
            },
        )

    # --- Duplicate check ---------------------------------------------------
    # Query guild_members for a record matching BOTH org_name AND
    # contact_email (case-insensitive). If a match exists -> HTTP 409.
    #
    # The check is best-effort: if the guild_members table does not exist yet
    # (or any other Supabase error occurs on the select), we log it and fall
    # through to issue the credential -- an unprovisioned table must not block
    # signup. Only a *successful* select that returns a matching row blocks it.
    #
    # NOTE: PostgREST `ilike` treats `%`, `_` and `\` as LIKE wildcards, so we
    # escape them to force an exact (case-insensitive) comparison and avoid
    # both false positives (wrong 409) and false negatives (missed duplicate).
    client = get_supabase()
    if client is not None:
        duplicate_found = False
        try:
            existing = (
                client.table("guild_members")
                .select("id")
                .eq("contact_email", contact_email.lower().strip())
                .eq("org_name", org_name.strip())
                .limit(1)
                .execute()
            )
            # A clean select succeeded -- trust its result.
            duplicate_found = bool(getattr(existing, "data", None))
        except Exception as exc:
            # Table not provisioned yet, RLS/permission issue, or transient
            # error. Skip the duplicate check and proceed (acceptable for now).
            _guild_logger.warning(
                "Guild duplicate check skipped (select failed): %s", exc
            )
            duplicate_found = False

        if duplicate_found:
            return JSONResponse(
                status_code=409,
                content={
                    "error": "already_registered",
                    "message": "This org/email combination is already registered.",
                    "credential_note": "Contact guild@zeroeng.io to retrieve your existing credential.",
                },
            )

    # --- Sign the JWT credential ---
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(days=365)
    payload = {
        "sub": contact_email,
        "org": org_name,
        "role": role,
        "tier": "free",
        "iss": "build-guild.zeroeng.io",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    project_credential = jwt.encode(payload, _guild_jwt_secret(), algorithm="HS256")

    # --- Persist to Supabase (best-effort) ---
    if client is not None:
        row = {
            "org_name": org_name.strip(),
            "role": role,
            "contact_name": contact_name.strip(),
            "contact_email": contact_email.lower().strip(),
            "tier": "free",
            "status": "active",
            "project_credential": project_credential,
            "created_at": now.isoformat(),
        }
        if a2a_endpoint:
            row["a2a_endpoint"] = a2a_endpoint
        try:
            client.table("guild_members").insert(row).execute()
        except Exception as exc:
            # If the a2a_endpoint column is not yet provisioned, retry without it.
            if "a2a_endpoint" in row:
                _guild_logger.warning(
                    "Insert with a2a_endpoint failed (%s); retrying without it. "
                    "Run migration: ALTER TABLE public.guild_members "
                    "ADD COLUMN IF NOT EXISTS a2a_endpoint TEXT;",
                    exc,
                )
                row.pop("a2a_endpoint", None)
                try:
                    client.table("guild_members").insert(row).execute()
                except Exception as exc2:
                    _guild_logger.error("Guild member insert failed: %s", exc2)
            else:
                # Table may not exist yet -- still return the credential so the
                # endpoint is testable before the table is provisioned.
                _guild_logger.error("Guild member insert failed: %s", exc)
    else:
        _guild_logger.warning(
            "Supabase not configured; guild member for %s not persisted.",
            contact_email,
        )

    # --- Success ---
    return JSONResponse(
        status_code=201,
        content={
            "status": "registered",
            "org_name": org_name,
            "role": role,
            "tier": "free",
            "a2a_endpoint": a2a_endpoint or None,
            "project_credential": project_credential,
            "instructions": {
                "how_to_use": "Include this credential in the Authorization header of all Build Guild requests.",
                "header_format": "Authorization: Bearer <project_credential>",
                "mcp_endpoint": "https://www.zeroeng.io/mcp",
                "marketplace": "https://www.zeroeng.io/build-guild",
                "support": "guild@zeroeng.io",
            },
            "capabilities": [
                "Verified vendor profile in the Build Guild marketplace",
                "Access to public MCP geospatial tools (soils, flood zones, wetlands, OSM)",
                "Receive RFPs addressed to your organization",
                "Participate in project-scoped marketplace activity when invited",
            ],
        },
    )



# ---------------------------------------------------------------------------
# Build Guild registration -- MCP tool wrapper
# ---------------------------------------------------------------------------
# Mirrors the POST /build-guild/register logic, but returns an MCP text result
# so an agent can complete the entire registration inside its LLM session via
# the MCP protocol (tools/call) -- no browser or external HTTP client required.


def build_guild_register_tool(
    org_name: Any,
    role: Any,
    contact_name: Any,
    contact_email: Any,
    a2a_endpoint: Any = None,
) -> dict:
    """Register an org with the Build Guild and return an MCP text result."""
    # --- Normalize inputs ---
    org_name = org_name.strip() if isinstance(org_name, str) else org_name
    role = role.strip() if isinstance(role, str) else role
    contact_name = contact_name.strip() if isinstance(contact_name, str) else contact_name
    contact_email = contact_email.strip() if isinstance(contact_email, str) else contact_email
    a2a_endpoint = a2a_endpoint.strip() if isinstance(a2a_endpoint, str) else a2a_endpoint

    # --- Validate required fields ---
    missing = [
        field
        for field, value in (
            ("org_name", org_name),
            ("role", role),
            ("contact_name", contact_name),
            ("contact_email", contact_email),
        )
        if not value
    ]
    if missing:
        return _tool_text(
            "Registration failed — missing required field(s): "
            + ", ".join(missing)
            + ". Please provide org_name, role, contact_name, and contact_email.",
            is_error=True,
        )

    # --- Validate role ---
    if role not in VALID_GUILD_ROLES:
        return _tool_text(
            f"Registration failed — invalid role '{role}'. "
            "Must be one of: " + ", ".join(sorted(VALID_GUILD_ROLES)) + ".",
            is_error=True,
        )

    # --- Duplicate check (best-effort; uses exact .eq() matching) ---
    client = get_supabase()
    if client is not None:
        duplicate_found = False
        try:
            existing = (
                client.table("guild_members")
                .select("id")
                .eq("contact_email", contact_email.lower())
                .eq("org_name", org_name)
                .limit(1)
                .execute()
            )
            duplicate_found = bool(getattr(existing, "data", None))
        except Exception as exc:
            _guild_logger.warning(
                "Guild duplicate check skipped (select failed): %s", exc
            )
            duplicate_found = False

        if duplicate_found:
            return _tool_text(
                f"'{org_name}' ({contact_email}) is already registered with "
                "The Build Guild. Each org/email combination can only be "
                "registered once. To retrieve your existing project credential, "
                "contact guild@zeroeng.io.",
                is_error=False,
            )

    # --- Sign the JWT credential ---
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(days=365)
    payload = {
        "sub": contact_email,
        "org": org_name,
        "role": role,
        "tier": "free",
        "iss": "build-guild.zeroeng.io",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    project_credential = jwt.encode(payload, _guild_jwt_secret(), algorithm="HS256")

    # --- Persist to Supabase (best-effort) ---
    write_error = None
    if client is not None:
        row = {
            "org_name": org_name,
            "role": role,
            "contact_name": contact_name,
            "contact_email": contact_email.lower(),
            "tier": "free",
            "status": "active",
            "project_credential": project_credential,
            "created_at": now.isoformat(),
        }
        if a2a_endpoint:
            row["a2a_endpoint"] = a2a_endpoint
        try:
            client.table("guild_members").insert(row).execute()
        except Exception as exc:
            # If the a2a_endpoint column is not yet provisioned, retry without it
            # so registration still succeeds.
            if "a2a_endpoint" in row:
                _guild_logger.warning(
                    "Insert with a2a_endpoint failed (%s); retrying without it. "
                    "Run migration: ALTER TABLE public.guild_members "
                    "ADD COLUMN IF NOT EXISTS a2a_endpoint TEXT;",
                    exc,
                )
                row.pop("a2a_endpoint", None)
                try:
                    client.table("guild_members").insert(row).execute()
                except Exception as exc2:
                    _guild_logger.error("Guild member insert failed (MCP tool): %s", exc2)
                    write_error = f"{type(exc2).__name__}: {exc2}"
            else:
                _guild_logger.error("Guild member insert failed (MCP tool): %s", exc)
                write_error = f"{type(exc).__name__}: {exc}"
    else:
        _guild_logger.warning(
            "Supabase not configured; guild member for %s not persisted.",
            contact_email,
        )
        write_error = "Supabase client not configured (SUPABASE_URL / SUPABASE_ANON_KEY missing)."

    # --- Success message ---
    bar = "\u2501" * 38
    message = (
        "\u2705 Registration successful — welcome to The Build Guild!\n\n"
        f"Org: {org_name}\n"
        f"Role: {role}\n"
        "Tier: Free ($0)\n"
        f"Contact: {contact_name} {contact_email}\n"
        + (f"A2A endpoint: {a2a_endpoint}\n" if a2a_endpoint else "")
        + "Issued by: build-guild.zeroeng.io\n"
        "Valid: 365 days\n\n"
        f"{bar}\n"
        "YOUR PROJECT CREDENTIAL (save this now)\n"
        f"{bar}\n"
        f"{project_credential}\n\n"
        f"{bar}\n"
        "HOW TO USE\n"
        f"{bar}\n"
        "Add this header to all authenticated Build Guild requests:\n"
        "Authorization: Bearer <project_credential>\n\n"
        "Your current capabilities (free tier):\n"
        "\u2022 Verified vendor profile in the Build Guild marketplace\n"
        "\u2022 Access to all public MCP geospatial tools (soils, flood zones, wetlands, OSM)\n"
        "\u2022 Receive RFPs addressed to your organization\n"
        "\u2022 Participate in project-scoped marketplace activity when invited\n\n"
        "Next step: Connect the Zero Engineering MCP server to your agent:\n"
        "https://www.zeroeng.io/mcp  (streamable-http, JSON-RPC 2.0, no auth required for public tools)\n\n"
        "Support: guild@zeroeng.io"
    )
    if write_error:
        message += f"\n\n\u26a0\ufe0f Supabase write failed: {write_error}"
    return _tool_text(message, is_error=False)



# ---------------------------------------------------------------------------
# A2A (Agent-to-Agent) protocol support
# ---------------------------------------------------------------------------
# The Build Guild speaks Google's open A2A spec (https://google.github.io/A2A/):
#   * Publishes an Agent Card at GET /.well-known/agent.json
#   * Exposes a JSON-RPC 2.0 endpoint at POST /a2a
#   * Brokers a member-agent directory so registered firms can discover and
#     call each other's A2A endpoints directly.
#
# Supabase migration required for the member-agent directory:
#   ALTER TABLE public.guild_members ADD COLUMN IF NOT EXISTS a2a_endpoint TEXT;
# (Attempted automatically at startup via the Supabase Management API when
#  SUPABASE_SERVICE_ROLE_KEY + SUPABASE_PROJECT_REF are set; otherwise logged.)

A2A_ENDPOINT_URL = "https://www.zeroeng.io/a2a"

AGENT_CARD = {
    "name": "The Build Guild",
    "description": (
        "A secure, AHJ-sanctioned agent-to-agent marketplace for the built environment. "
        "AI agents representing licensed architects, engineers, contractors, vendors, and owners "
        "connect, discover, and communicate directly — authenticated by jurisdiction and scoped by role."
    ),
    "url": A2A_ENDPOINT_URL,
    "iconUrl": "https://www.zeroeng.io/favicon.ico",
    "version": "0.1.0",
    "documentationUrl": "https://www.zeroeng.io/build-guild",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False,
    },
    "authentication": {
        "schemes": ["Bearer"],
        "credentials": (
            "project_credential JWT issued on registration. Required for "
            "find_agents and verify_credential. Optional for register "
            "(unauthenticated registration is permitted)."
        ),
    },
    "defaultInputModes": ["application/json", "text/plain"],
    "defaultOutputModes": ["application/json", "text/plain"],
    "skills": [
        {
            "id": "register",
            "name": "Register Organization",
            "description": (
                "Register a firm with The Build Guild. Returns a "
                "project_credential JWT valid for 365 days. Optionally include "
                "your firm's own A2A endpoint to be discoverable by other agents."
            ),
            "tags": ["registration", "onboarding", "marketplace"],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
            "examples": [
                "Register Acme Engineering as an Engineer with contact Jane Doe at jane@acme-eng.example"
            ],
        },
        {
            "id": "find_agents",
            "name": "Find Agents",
            "description": (
                "Search the Build Guild member directory for registered "
                "organizations. Filter by role (Architect, Engineer, Contractor, "
                "Vendor, Owner). Optionally restrict to members with A2A "
                "endpoints for direct agent communication."
            ),
            "tags": ["discovery", "directory", "agents"],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
            "examples": [
                "Find all registered Engineers with A2A endpoints",
                "Show me Contractor members",
            ],
        },
        {
            "id": "verify_credential",
            "name": "Verify Credential",
            "description": (
                "Verify a Build Guild project_credential JWT. Returns the "
                "decoded identity (org, role, tier) if valid, or an error if "
                "expired or tampered."
            ),
            "tags": ["auth", "verification", "identity"],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"],
            "examples": ["Verify this JWT: eyJ..."],
        },
    ],
}

A2A_SKILLS_SUMMARY = {
    "register": "Register a firm; returns a 365-day project_credential JWT. "
                "Arguments: org_name, role, contact_name, contact_email, "
                "a2a_endpoint (optional).",
    "find_agents": "Search the member directory (Bearer token required). "
                   "Arguments: role (optional), a2a_only (optional bool), "
                   "search (optional).",
    "verify_credential": "Decode/validate a project_credential JWT. "
                         "Arguments: token.",
}


# ── A2A skill handlers ─────────────────────────────────────────────────────

def _a2a_skill_register(arguments: dict, auth_header: Optional[str]) -> dict:
    """A2A register skill — wraps build_guild_register_tool, returns a data dict."""
    arguments = arguments or {}
    org_name = arguments.get("org_name")
    role = arguments.get("role")
    contact_name = arguments.get("contact_name")
    contact_email = arguments.get("contact_email")
    a2a_endpoint = arguments.get("a2a_endpoint")

    result = build_guild_register_tool(
        org_name, role, contact_name, contact_email, a2a_endpoint
    )
    # build_guild_register_tool returns an MCP-style text result. Extract text
    # and pull the project_credential (JWT) if registration succeeded.
    text = ""
    try:
        text = result["content"][0]["text"]
    except Exception:
        text = str(result)
    is_error = bool(result.get("isError"))

    credential = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("eyJ") and "." in line:
            credential = line
            break

    data = {
        "skill": "register",
        "ok": not is_error and credential is not None,
        "message": text,
    }
    if credential:
        data.update(
            {
                "status": "registered",
                "org_name": (org_name.strip() if isinstance(org_name, str) else org_name),
                "role": role,
                "tier": "free",
                "a2a_endpoint": (a2a_endpoint.strip() if isinstance(a2a_endpoint, str) else a2a_endpoint) or None,
                "project_credential": credential,
                "how_to_use": "Authorization: Bearer <project_credential>",
            }
        )
    return data


def _a2a_skill_find_agents(arguments: dict, auth_header: Optional[str]) -> dict:
    """A2A find_agents skill — requires a Bearer token in auth_header."""
    arguments = arguments or {}
    token = _extract_bearer(auth_header)
    # Allow the token to also be passed explicitly in arguments as a fallback.
    if not token:
        token = arguments.get("project_credential") or arguments.get("token")

    verify = _guild_verify_jwt(token)
    if not verify["valid"]:
        return {
            "skill": "find_agents",
            "ok": False,
            "error": "unauthorized",
            "message": (
                "find_agents requires a valid Build Guild credential. Present it "
                "as 'Authorization: Bearer <project_credential>'. "
                f"({verify['error']})"
            ),
        }

    role = arguments.get("role")
    if role and role not in VALID_GUILD_ROLES:
        return {
            "skill": "find_agents",
            "ok": False,
            "error": "invalid_role",
            "message": "Invalid role. Must be one of: "
            + ", ".join(sorted(VALID_GUILD_ROLES)) + ".",
        }

    result = _query_guild_directory(
        role=role,
        a2a_only=bool(arguments.get("a2a_only")),
        search=arguments.get("search"),
    )
    if not result["ok"]:
        return {
            "skill": "find_agents",
            "ok": False,
            "error": "query_failed",
            "message": result["error"],
        }
    return {
        "skill": "find_agents",
        "ok": True,
        "count": len(result["members"]),
        "members": result["members"],
        "queried_by": verify["claims"].get("org"),
    }


def _a2a_skill_verify_credential(arguments: dict) -> dict:
    """A2A verify_credential skill — decode + validate a JWT."""
    arguments = arguments or {}
    token = arguments.get("token") or arguments.get("project_credential")
    verify = _guild_verify_jwt(token)
    if not verify["valid"]:
        return {
            "skill": "verify_credential",
            "ok": False,
            "valid": False,
            "error": verify["error"],
        }
    claims = verify["claims"]
    now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    exp = claims.get("exp")
    expires_in_days = None
    if isinstance(exp, (int, float)):
        expires_in_days = round((exp - now_ts) / 86400, 1)
    return {
        "skill": "verify_credential",
        "ok": True,
        "valid": True,
        "org": claims.get("org"),
        "role": claims.get("role"),
        "tier": claims.get("tier"),
        "sub": claims.get("sub"),
        "iss": claims.get("iss"),
        "iat": claims.get("iat"),
        "exp": exp,
        "expires_in_days": expires_in_days,
    }


# ── A2A JSON-RPC helpers ───────────────────────────────────────────────────

def _a2a_task_result(task_id: Any, state: str, data: Any = None,
                     text: Optional[str] = None) -> dict:
    """Build an A2A Task object (per the A2A spec) for a JSON-RPC result."""
    parts = []
    if data is not None:
        parts.append({"type": "data", "data": data})
    if text is not None:
        parts.append({"type": "text", "text": text})
    return {
        "id": task_id,
        "status": {
            "state": state,
            "message": {
                "role": "agent",
                "parts": parts,
            },
        },
        "artifacts": [],
    }


def _a2a_dispatch_skill(skill: str, arguments: dict,
                        auth_header: Optional[str]) -> tuple:
    """Route a skill call. Returns (state, data_dict)."""
    if skill == "register":
        data = _a2a_skill_register(arguments, auth_header)
        return ("completed", data)
    if skill == "find_agents":
        data = _a2a_skill_find_agents(arguments, auth_header)
        state = "completed" if data.get("ok") else "failed"
        return (state, data)
    if skill == "verify_credential":
        data = _a2a_skill_verify_credential(arguments)
        state = "completed" if data.get("ok") else "failed"
        return (state, data)
    return (
        "failed",
        {
            "ok": False,
            "error": "unknown_skill",
            "message": f"Unknown skill '{skill}'.",
            "available_skills": A2A_SKILLS_SUMMARY,
        },
    )


def _a2a_extract_skill_call(message: dict) -> tuple:
    """From an A2A message, extract (skill, arguments) or (None, None).

    Prefers a `data` part with {"skill": ..., "arguments": {...}}. Falls back
    to inspecting a `text` part (returns skill=None so the caller can emit a
    helpful error).
    """
    parts = (message or {}).get("parts") or []
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "data" and isinstance(part.get("data"), dict):
            d = part["data"]
            skill = d.get("skill")
            arguments = d.get("arguments") or {}
            if skill:
                return (skill, arguments)
    # No structured data part -- return the first text (for a NL fallback).
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            return (None, {"_text": part.get("text", "")})
    return (None, None)


def _handle_a2a_rpc(message: dict) -> Optional[dict]:
    """Handle a single A2A JSON-RPC 2.0 message."""
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    auth_header = message.get("_auth_header")  # injected by the endpoint

    if method in ("tasks/send", "message/send"):
        task_id = params.get("id") or params.get("taskId")
        msg = params.get("message") or {}
        skill, arguments = _a2a_extract_skill_call(msg)

        if skill is None:
            # Natural-language / no structured skill call -- return a helpful
            # error listing the available skills.
            help_data = {
                "ok": False,
                "error": "no_skill_specified",
                "message": (
                    "No skill was specified. Send a message with a 'data' part: "
                    '{"skill": "<register|find_agents|verify_credential>", '
                    '"arguments": {...}}.'
                ),
                "available_skills": A2A_SKILLS_SUMMARY,
            }
            if arguments and arguments.get("_text"):
                help_data["received_text"] = arguments.get("_text")
            return _rpc_result(
                msg_id, _a2a_task_result(task_id, "failed", data=help_data)
            )

        state, data = _a2a_dispatch_skill(skill, arguments, auth_header)
        return _rpc_result(msg_id, _a2a_task_result(task_id, state, data=data))

    if method == "tasks/get":
        # We don't persist task history in this version.
        return _rpc_error(
            msg_id, -32001,
            "Task history is not persisted in this version of the Build Guild A2A agent."
        )

    if method == "tasks/cancel":
        task_id = params.get("id") or params.get("taskId")
        return _rpc_result(
            msg_id, _a2a_task_result(task_id, "canceled",
                                     data={"ok": True, "message": "Task canceled."})
        )

    if method == "agent/authenticatedExtendedCard":
        return _rpc_result(msg_id, AGENT_CARD)

    return _rpc_error(msg_id, -32601, f"Method not found: {method}")


@app.get("/.well-known/agent.json")
async def well_known_agent_card():
    """A2A Agent Card (Google A2A spec)."""
    return JSONResponse(content=AGENT_CARD)


@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A JSON-RPC 2.0 endpoint for The Build Guild."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            _rpc_error(None, -32700, "Parse error: invalid JSON"), status_code=400
        )

    auth_header = request.headers.get("authorization")

    if isinstance(payload, list):
        for m in payload:
            if isinstance(m, dict):
                m["_auth_header"] = auth_header
        responses = [r for r in (_handle_a2a_rpc(m) for m in payload if isinstance(m, dict)) if r is not None]
        return JSONResponse(content=responses)

    if not isinstance(payload, dict):
        return JSONResponse(
            _rpc_error(None, -32600, "Invalid Request"), status_code=400
        )

    payload["_auth_header"] = auth_header
    response = _handle_a2a_rpc(payload)
    if response is None:
        return JSONResponse(content=None, status_code=202)
    return JSONResponse(content=response)


# ---------------------------------------------------------------------------
# Startup: attempt the a2a_endpoint column migration (best-effort)
# ---------------------------------------------------------------------------

_A2A_MIGRATION_SQL = (
    "ALTER TABLE public.guild_members ADD COLUMN IF NOT EXISTS a2a_endpoint TEXT;"
)


def _run_a2a_migration() -> None:
    """Best-effort: add the a2a_endpoint column via the Supabase Management API.

    PostgREST (anon key) cannot run DDL, so this uses the Supabase Management
    API when SUPABASE_SERVICE_ROLE_KEY + SUPABASE_PROJECT_REF are available.
    If neither works, we log the SQL to run manually -- the code paths above
    all tolerate the column being absent.
    """
    project_ref = os.environ.get("SUPABASE_PROJECT_REF")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    mgmt_token = os.environ.get("SUPABASE_ACCESS_TOKEN")

    # Route 1: Supabase Management API (requires a personal access token).
    if project_ref and mgmt_token:
        try:
            import urllib.request

            url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
            body = json.dumps({"query": _A2A_MIGRATION_SQL}).encode("utf-8")
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={
                    "Authorization": f"Bearer {mgmt_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    _guild_logger.info(
                        "A2A migration applied via Supabase Management API."
                    )
                    return
        except Exception as exc:
            _guild_logger.warning(
                "A2A migration via Management API failed: %s", exc
            )

    # Route 2: PostgREST RPC 'exec_sql' if the project happens to expose one.
    if service_key and os.environ.get("SUPABASE_URL"):
        try:
            import urllib.request

            url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/rpc/exec_sql"
            body = json.dumps({"sql": _A2A_MIGRATION_SQL}).encode("utf-8")
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201, 204):
                    _guild_logger.info("A2A migration applied via exec_sql RPC.")
                    return
        except Exception as exc:
            _guild_logger.warning("A2A migration via exec_sql RPC failed: %s", exc)

    # Fallback: log the SQL to run manually. Column-absent is handled gracefully.
    _guild_logger.warning(
        "A2A migration NOT applied automatically. Run this SQL manually in the "
        "Supabase SQL editor:\n    %s", _A2A_MIGRATION_SQL
    )


# ---------------------------------------------------------------------------
# Startup: agents / agent_messages schema migration (best-effort)
# ---------------------------------------------------------------------------
# Full, idempotent DDL for the agent registry. Mirrors
# supabase/migrations/0001_agents.sql (kept in sync). Applied at startup via the
# Supabase Management API when SUPABASE_ACCESS_TOKEN + SUPABASE_PROJECT_REF are
# set; otherwise the SQL is logged to run manually. All code paths tolerate the
# tables being absent, so a missing migration never crashes the app.
_AGENTS_MIGRATION_SQL = """
ALTER TABLE public.organizations ADD COLUMN IF NOT EXISTS domain text;
CREATE INDEX IF NOT EXISTS organizations_domain_idx ON public.organizations (lower(domain));

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_type') THEN
    CREATE TYPE agent_type AS ENUM ('company', 'project');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agent_status') THEN
    CREATE TYPE agent_status AS ENUM ('pending', 'approved', 'offline');
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS public.agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  type agent_type NOT NULL,
  org_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  project_id uuid REFERENCES public.projects(id) ON DELETE CASCADE,
  created_by uuid NOT NULL REFERENCES auth.users(id),
  agent_url text NOT NULL,
  discovery_card jsonb,
  status agent_status NOT NULL DEFAULT 'pending',
  approved_at timestamptz,
  last_ping timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agents_org_id_idx ON public.agents (org_id);
CREATE INDEX IF NOT EXISTS agents_project_id_idx ON public.agents (project_id);

CREATE TABLE IF NOT EXISTS public.agent_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  project_id uuid REFERENCES public.projects(id) ON DELETE CASCADE,
  conversation_id text,
  sender text NOT NULL,
  from_firm text,
  body text NOT NULL,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS agent_messages_agent_id_idx ON public.agent_messages (agent_id, created_at);
CREATE INDEX IF NOT EXISTS agent_messages_conversation_idx ON public.agent_messages (conversation_id);

ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS agents_select_org_members ON public.agents;
CREATE POLICY agents_select_org_members ON public.agents FOR SELECT TO authenticated
  USING (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.org_id = agents.org_id AND m.user_id = auth.uid()));

DROP POLICY IF EXISTS agents_insert_company_admin ON public.agents;
CREATE POLICY agents_insert_company_admin ON public.agents FOR INSERT TO authenticated
  WITH CHECK (created_by = auth.uid() AND (
    (type = 'company' AND project_id IS NULL AND EXISTS (
       SELECT 1 FROM public.organization_members m WHERE m.org_id = agents.org_id AND m.user_id = auth.uid() AND lower(m.role) = 'admin'))
    OR (type = 'project' AND project_id IS NOT NULL AND (
       EXISTS (SELECT 1 FROM public.projects p WHERE p.id = agents.project_id AND p.owner_id = auth.uid())
       OR EXISTS (SELECT 1 FROM public.project_members pm WHERE pm.project_id = agents.project_id AND pm.user_id = auth.uid())))));

DROP POLICY IF EXISTS agents_update_authorized ON public.agents;
CREATE POLICY agents_update_authorized ON public.agents FOR UPDATE TO authenticated
  USING (
    (type = 'company' AND EXISTS (SELECT 1 FROM public.organization_members m WHERE m.org_id = agents.org_id AND m.user_id = auth.uid() AND lower(m.role) = 'admin'))
    OR (type = 'project' AND (
       EXISTS (SELECT 1 FROM public.projects p WHERE p.id = agents.project_id AND p.owner_id = auth.uid())
       OR EXISTS (SELECT 1 FROM public.project_members pm WHERE pm.project_id = agents.project_id AND pm.user_id = auth.uid())
       OR EXISTS (SELECT 1 FROM public.organization_members m WHERE m.org_id = agents.org_id AND m.user_id = auth.uid() AND lower(m.role) = 'admin'))));

DROP POLICY IF EXISTS agent_messages_select_org ON public.agent_messages;
CREATE POLICY agent_messages_select_org ON public.agent_messages FOR SELECT TO authenticated
  USING (EXISTS (SELECT 1 FROM public.agents a JOIN public.organization_members m ON m.org_id = a.org_id WHERE a.id = agent_messages.agent_id AND m.user_id = auth.uid()));

DROP POLICY IF EXISTS agent_messages_insert_org ON public.agent_messages;
CREATE POLICY agent_messages_insert_org ON public.agent_messages FOR INSERT TO authenticated
  WITH CHECK (EXISTS (SELECT 1 FROM public.agents a JOIN public.organization_members m ON m.org_id = a.org_id WHERE a.id = agent_messages.agent_id AND m.user_id = auth.uid()));

DROP POLICY IF EXISTS agents_app_all ON public.agents;
CREATE POLICY agents_app_all ON public.agents FOR ALL TO anon USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS agent_messages_app_all ON public.agent_messages;
CREATE POLICY agent_messages_app_all ON public.agent_messages FOR ALL TO anon USING (true) WITH CHECK (true);
"""


def _run_agents_migration() -> None:
    """Best-effort apply of the agents schema via the Supabase Management API."""
    project_ref = os.environ.get("SUPABASE_PROJECT_REF")
    mgmt_token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if project_ref and mgmt_token:
        try:
            import urllib.request

            url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
            body = json.dumps({"query": _AGENTS_MIGRATION_SQL}).encode("utf-8")
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={
                    "Authorization": f"Bearer {mgmt_token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status in (200, 201):
                    _guild_logger.info(
                        "Agents migration applied via Supabase Management API."
                    )
                    return
        except Exception as exc:
            _guild_logger.warning(
                "Agents migration via Management API failed: %s", exc
            )
    _guild_logger.warning(
        "Agents migration NOT applied automatically. Run "
        "supabase/migrations/0001_agents.sql in the Supabase SQL editor."
    )


@app.on_event("startup")
async def _a2a_startup():
    try:
        _run_a2a_migration()
    except Exception as exc:  # never let migration crash startup
        _guild_logger.warning("A2A startup migration skipped: %s", exc)
    try:
        _run_agents_migration()
    except Exception as exc:  # never let migration crash startup
        _guild_logger.warning("Agents startup migration skipped: %s", exc)
