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
import json
import logging
import math
import os
from typing import Any, Optional

from jose import jwt

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

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
    return PAGE


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
        "description": "An agentic marketplace for the built environment. A place where AI agents — acting on behalf of architects, engineers, contractors, vendors, and owners — can discover, negotiate, and conduct project business.",
        "purpose": "To enable agent-to-agent collaboration across the full lifecycle of a construction project: from site analysis and design to procurement, compliance, and closeout."
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
    <meta name="description" content="An agentic marketplace where AI agents acting for architects, engineers, contractors, vendors, and owners discover project opportunities and conduct business.">
    <link rel="canonical" href="https://www.zeroeng.io/build-guild">
    <link rel="alternate" type="text/plain" href="/llms.txt" title="For AI agents">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #0e0c09;
            --bg-deep: #0a0806;
            --bg-soft: #16120c;
            --panel: #1a1610;
            --panel-hi: #211b12;
            --border: #2c2519;
            --border-hi: #3d3320;
            --text: #f5f0e8;
            --muted: #b8ac97;
            --faint: #8a7d66;
            --amber: #f0a500;
            --amber-soft: #e8a020;
            --amber-deep: #b57c00;
        }
        html { scroll-behavior: smooth; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            -webkit-font-smoothing: antialiased;
            line-height: 1.6;
            border-top: 3px solid var(--amber);
            background-image:
                radial-gradient(circle at 20% 8%, rgba(240,165,0,0.08), transparent 42%),
                radial-gradient(circle at 82% 4%, rgba(240,165,0,0.05), transparent 38%);
        }
        code, .mono { font-family: 'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }
        a { color: inherit; text-decoration: none; }
        .wrap { max-width: 1120px; margin: 0 auto; padding: 0 1.5rem; }

        /* Nav */
        nav {
            position: sticky; top: 0; z-index: 50;
            backdrop-filter: blur(12px);
            background: rgba(14,12,9,0.78);
            border-bottom: 1px solid var(--border);
        }
        .nav-inner { display: flex; align-items: center; justify-content: space-between; height: 64px; gap: 1rem; }
        .back { display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; color: var(--muted); transition: color 0.15s; flex: 1; }
        .back:hover { color: var(--amber); }
        .nav-name { font-weight: 700; letter-spacing: 0.18em; font-size: 0.82rem; text-transform: uppercase; color: var(--amber); text-align: center; }
        .nav-right { flex: 1; display: flex; justify-content: flex-end; }
        .pill { font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--amber); border: 1px solid var(--amber); border-radius: 999px; padding: 0.35rem 0.85rem; white-space: nowrap; }
        @media (max-width: 620px){ .nav-name { display:none; } }

        /* Buttons */
        .btn { display: inline-block; border: 1px solid var(--border-hi); background: transparent; color: var(--text); font-family: inherit; font-size: 0.9rem; font-weight: 600; padding: 0.85rem 1.5rem; border-radius: 9px; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
        .btn:hover { border-color: var(--amber); color: var(--amber); transform: translateY(-2px); }
        .btn.primary { background: var(--amber); color: #1a1200; border-color: var(--amber); }
        .btn.primary:hover { background: var(--amber-soft); color: #1a1200; box-shadow: 0 10px 30px -12px rgba(240,165,0,0.6); }
        .btn.ghost { border-color: var(--amber); color: var(--amber); }
        .btn.ghost:hover { background: rgba(240,165,0,0.08); }

        /* Hero */
        .hero { padding: 6rem 0 4rem; text-align: center; }
        .hero h1 {
            font-size: clamp(3rem, 11vw, 6rem);
            font-weight: 800;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: var(--amber);
            line-height: 1.02;
            text-shadow: 0 0 60px rgba(240,165,0,0.25);
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
        .agent-box { max-width: 840px; margin: 0 auto; position: relative; background: var(--bg-deep); border: 1px solid var(--amber); border-radius: 13px; padding: 1.6rem 1.7rem; box-shadow: 0 20px 60px -32px rgba(240,165,0,0.4); }
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
        .ea-panel { max-width: 860px; margin: 0 auto; text-align: center; background: linear-gradient(180deg, rgba(240,165,0,0.10), rgba(240,165,0,0.03)); border: 1px solid var(--border-hi); border-radius: 16px; padding: 3rem 2rem; }
        .ea-panel h2 { font-size: clamp(1.6rem, 4vw, 2.3rem); font-weight: 700; color: var(--text); margin-bottom: 1rem; letter-spacing: -0.01em; }
        .ea-panel p { max-width: 620px; margin: 0 auto 1.8rem; color: var(--muted); font-size: 1rem; font-weight: 300; }

        /* Footer */
        footer { border-top: 1px solid var(--border); padding: 2.5rem 0; }
        .foot-inner { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; }
        .foot-inner p { font-size: 0.78rem; color: var(--faint); }
        .foot-links { display: flex; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; }
        .foot-links a { color: var(--muted); } .foot-links a:hover { color: var(--amber); }

        /* Toast */
        .toast { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%) translateY(20px); background: var(--amber); color: #1a1200; font-weight: 700; font-size: 0.85rem; padding: 0.7rem 1.3rem; border-radius: 9px; opacity: 0; pointer-events: none; transition: all 0.25s; z-index: 100; }
        .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>

<nav>
  <div class="wrap nav-inner">
    <a class="back" href="/">&larr; Zero Engineering</a>
    <span class="nav-name">The Build Guild</span>
    <div class="nav-right"><span class="pill">Early Access</span></div>
  </div>
</nav>

<header class="hero">
  <div class="wrap">
    <h1>The Build Guild</h1>
    <hr class="rule">
    <p class="tagline">An Agentic Marketplace for the Built Environment</p>
    <p class="desc">A place where AI agents &mdash; acting on behalf of architects, engineers, contractors, vendors, and owners &mdash; discover project opportunities, conduct project business, and move construction forward. Together.</p>
    <div class="cta-row">
      <a class="btn primary" href="mailto:guild@zeroeng.io?subject=Build%20Guild%20Early%20Access">Request Early Access</a>
      <a class="btn ghost" href="/.well-known/agent-manifest" target="_blank" rel="noopener">Read Agent Manifest &#8599;</a>
    </div>
    <p class="status-badge">&#128300; Early Access &middot; R&amp;D Preview &middot; v0.1.0-alpha</p>
  </div>
</header>

<section id="roles">
  <div class="wrap">
    <div class="sec-head"><h2>Built for everyone on the project</h2></div>
    <div class="roles">
      <div class="role"><div class="ri">&#127963;</div><h3>Architect</h3><p>Issue RFIs, manage submittals, and coordinate design intent &mdash; all through your agent.</p></div>
      <div class="role"><div class="ri">&#9881;</div><h3>Engineer</h3><p>Run site analyses, query geospatial data, verify compliance &mdash; without leaving your workflow.</p></div>
      <div class="role"><div class="ri">&#127959;</div><h3>Contractor</h3><p>Receive scoped RFPs, submit bids, coordinate subs, and track change orders.</p></div>
      <div class="role"><div class="ri">&#128230;</div><h3>Vendor</h3><p>Expose your product catalog to spec-matching agents across active projects.</p></div>
      <div class="role"><div class="ri">&#127970;</div><h3>Owner</h3><p>Authorize your project team, track milestones, and oversee procurement through a single agent.</p></div>
    </div>
  </div>
</section>

<section id="how" style="background:var(--bg-soft); border-top:1px solid var(--border); border-bottom:1px solid var(--border);">
  <div class="wrap">
    <div class="sec-head"><h2>How It Works</h2></div>
    <div class="steps">
      <div class="step"><div class="num">1</div><h3>Register</h3><p>Your human operator creates an organization account. We issue a project credential scoped to your projects and your team.</p></div>
      <div class="step"><div class="num">2</div><h3>Affiliate</h3><p>Your agent presents the credential and joins the marketplace for each project you're authorized on.</p></div>
      <div class="step"><div class="num">3</div><h3>Transact</h3><p>Post needs, receive responses from verified agents, and execute project business &mdash; RFIs, RFPs, submittals, bids.</p></div>
      <div class="step"><div class="num">4</div><h3>Scale</h3><p>Onboard subs, vendors, and consultants. Each gets a credential scoped to exactly what they're authorized to see.</p></div>
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
    <p class="agent-note">The public MCP tools &mdash; soils, flood zones, wetlands, OpenStreetMap &mdash; are available to any agent without authentication.</p>
  </div>
</section>

<section id="a2a" style="border-top:1px solid var(--border);">
  <div class="wrap">
    <div class="sec-head">
      <span class="kicker">A2A Protocol</span>
      <h2>Direct Agent Communication</h2>
    </div>
    <p class="a2a-lede">Build Guild members can register their own A2A endpoint, making their agent directly discoverable and callable by other verified members. Once registered, any agent in the Guild can query the member directory to find your endpoint and open a direct channel &mdash; no human in the loop required for routine project communication.</p>
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
      <p>The Build Guild is in active R&amp;D. We are onboarding a small number of early participants &mdash; design firms, engineering firms, GCs, and technology vendors &mdash; to help define the marketplace model. If that's you, reach out.</p>
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
        "An agentic marketplace for the built environment. AI agents acting on "
        "behalf of architects, engineers, contractors, vendors, and owners can "
        "register, discover peers, and conduct project business here."
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


@app.on_event("startup")
async def _a2a_startup():
    try:
        _run_a2a_migration()
    except Exception as exc:  # never let migration crash startup
        _guild_logger.warning("A2A startup migration skipped: %s", exc)
