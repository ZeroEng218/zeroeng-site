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

import json
import math
import os
from typing import Any, Optional

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
            <p class="tile-desc">Custom Model Context Protocol servers that give your AI agents secure, structured access to tools, data, and workflows. Live tools at <a href="/mcp">/mcp</a> (streamable HTTP, JSON-RPC 2.0): <code>state_capital_lookup</code> and <code>soil_lookup</code> — USDA SSURGO soil types &amp; GeoJSON boundaries by lat/lon.</p>
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
        "name": "state_capital_lookup",
        "description": "Look up the capital city of a US state",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "The name of the US state",
                }
            },
            "required": ["state"],
        },
    },
    {
        "name": "soil_lookup",
        "description": (
            "Look up USDA SSURGO soil types and boundaries for a given latitude "
            "and longitude. Returns soil map unit metadata and GeoJSON polygon "
            "boundaries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude (WGS84, decimal degrees)",
                },
                "lon": {
                    "type": "number",
                    "description": "Longitude (WGS84, decimal degrees)",
                },
                "radius_meters": {
                    "type": "number",
                    "description": (
                        "Search radius in meters around the point (default: 500)"
                    ),
                },
            },
            "required": ["lat", "lon"],
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
        if name == "state_capital_lookup":
            return _rpc_result(msg_id, state_capital_lookup(arguments.get("state", "")))
        if name == "soil_lookup":
            return _rpc_result(
                msg_id,
                soil_lookup(
                    arguments.get("lat"),
                    arguments.get("lon"),
                    arguments.get("radius_meters", 500),
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
