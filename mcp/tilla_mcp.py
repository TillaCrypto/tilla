"""
TILLA MCP server — let any AI agent pull the TILLA data set directly.
=====================================================================
Wraps the TILLA data API (https://api.tillacrypto.com, /v1/*) as Model Context
Protocol tools. Once a user adds this server to their agent (Claude Desktop /
Claude Code / Cursor / any MCP client), the agent can query TILLA on its own —
no browser, no copy-paste.

Every tool maps to one route of the API; `TOOL_ROUTES` names it.

What it serves:
  Raw venue data, derived indicators and our own Bitcoin node - crypto spot and
  derivatives, equities and ETFs, FX, rates and macro - every value on one UTC
  clock. Plans are nested; the plan is in the path.

Auth:
  Set TILLA_API_KEY to a key (tk_live_...). Get a free one at
  https://tillacrypto.com, or POST /v1/demo_key for one with no account.
  The keyless tools (about, status, tiers, markets, sample, health, docs) work
  without a key.

Config (env):
  TILLA_API_KEY        the caller's key. Optional for the keyless tools.
  TILLA_API_BASE       default https://api.tillacrypto.com  (dev: http://127.0.0.1:8898)
  TILLA_MCP_TRANSPORT  "stdio" (default, for local agents) or "http" (remote/hosted)
  TILLA_MCP_HOST       http transport bind host (default 127.0.0.1)
  TILLA_MCP_PORT       http transport port    (default 8971)

Run:
  Local (stdio):   python tilla_mcp.py
  Remote (http):   TILLA_MCP_TRANSPORT=http python tilla_mcp.py
"""
from __future__ import annotations

import json
import os

import httpx

API_BASE = os.environ.get("TILLA_API_BASE", "https://api.tillacrypto.com").rstrip("/")
API_KEY = os.environ.get("TILLA_API_KEY", "").strip()
SIGNUP_URL = "https://tillacrypto.com"
TIMEOUT = httpx.Timeout(30.0, connect=8.0)
LAYERS = ("raw", "derived", "node", "deep")   # deep: the hourly history before 2023-08-10

# The API route each tool calls.
TOOL_ROUTES = {
    "tilla_status": ("GET", "/v1/status"),
    "tilla_tiers": ("GET", "/v1/tiers"),
    "tilla_inventory": ("GET", "/v1/inventory"),
    "tilla_window": ("GET", "/v1/{tier}/raw/{lane}"),       # and /derived/ and /node/
    "tilla_latest": ("GET", "/v1/{tier}/raw/{lane}"),
    "tilla_usage": ("GET", "/v1/usage"),
}

INSTRUCTIONS = (
    "TILLA serves raw market data, derived indicators and its own Bitcoin node on one UTC "
    "clock. Call `tilla_docs` to read the whole manual (every call and plan) in one go. `tilla_tick` returns every series the key holds for the minute just closed in one call, and `tilla_changes` every repaired cell. Use `tilla_status` to check the feed is live and `tilla_tiers` to see the plans. "
    "With a key: call `tilla_inventory` FIRST to get the exact series names the key holds "
    "(never invent a name), then `tilla_latest` for the newest bar or `tilla_window` for a "
    "range (page with the returned `next_start` while `more` is true). For a whole market at once - "
    "every BTC series plus its ETFs and miners, or one stock, pair or commodity - call `tilla_markets` "
    "for the ids and `tilla_market` with one. `tilla_usage` shows "
    "the key's budget. If TILLA_API_KEY is missing, tell the user to get a free key at "
    + SIGNUP_URL + " ."
)


# ── http helpers ──────────────────────────────────────────────────────────────
def _headers(auth: bool) -> dict:
    h = {"Accept": "application/json", "User-Agent": "tilla-mcp/2.0"}
    if auth and API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def _need_key() -> dict | None:
    if not API_KEY:
        return {"error": "no_api_key",
                "message": "This tool needs a TILLA API key. Set the TILLA_API_KEY "
                           "environment variable to a tk_live_... key.",
                "get_a_free_key": SIGNUP_URL}
    return None


def _safe_json(r: httpx.Response) -> dict:
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {"raw": r.text[:500]}


def _get(path: str, auth: bool, params: dict | None = None) -> dict:
    """GET {API_BASE}{path}. Parsed JSON, or a structured {error,...} an agent can act on."""
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.get(API_BASE + path, headers=_headers(auth),
                      params={k: v for k, v in (params or {}).items() if v is not None})
    except Exception as e:  # noqa: BLE001  network / DNS / TLS
        return {"error": "unreachable",
                "message": "Could not reach the TILLA API at %s (%s)." % (API_BASE, type(e).__name__)}
    if r.status_code == 401:
        return {"error": "unauthorized", "status": 401,
                "message": "No API key was sent. Get a free key at " + SIGNUP_URL}
    if r.status_code == 403:
        return {"error": "forbidden", "status": 403,
                "message": _safe_json(r).get("error") or "That key or that data is outside the plan. "
                           "See tilla_tiers and tilla_inventory."}
    if r.status_code == 429:
        return {"error": "rate_limited", "status": 429,
                "retry_after_seconds": r.headers.get("Retry-After"),
                "remaining_this_minute": r.headers.get("X-RateLimit-Remaining"),
                "message": _safe_json(r).get("error") or "A rate limit or daily budget was hit."}
    if r.status_code >= 400:
        return {"error": "http_error", "status": r.status_code,
                "message": _safe_json(r).get("error", r.text[:200])}
    return _safe_json(r)


def _names(series) -> str | None:
    """Accept a list or a comma string; return the comma string the API expects."""
    if not series:
        return None
    if isinstance(series, (list, tuple)):
        return ",".join(str(c).strip() for c in series if str(c).strip())
    return ",".join(p.strip() for p in str(series).split(",") if p.strip())


_TIER = {"t": None}


def _my_tier() -> str | dict:
    """The key's own tier, asked once of /v1/usage - the tier goes in the data path."""
    if _TIER["t"]:
        return _TIER["t"]
    u = _get("/v1/usage", auth=True)
    if "tier" not in u:
        return u
    _TIER["t"] = u["tier"]
    return _TIER["t"]


# ── the tools, as plain functions (registered with MCP below) ────────────────
def tilla_about() -> dict:
    """What TILLA is, who it's for, and how to start. No API key needed."""
    return {
        "product": "TILLA - market data on one clock",
        "what": "Raw venue data, derived indicators computed from it bar by bar with no look-ahead, "
                "and blocks/mempool from our own Bitcoin node. Every value sits on a UTC bar labelled "
                "by the end of the period it covers; every bar is hashed as it lands.",
        "covers": ["crypto spot and derivatives (funding, open interest, long/short, options)",
                   "equities and ETFs", "FX", "commodity and index proxies", "rates and macro",
                   "sentiment and flows", "the Bitcoin node (Max and above)"],
        "empty_values": "A closed market carries its last real print; an open market with no print, "
                        "or a derived value with no mathematical answer, is empty - never invented.",
        "get_a_free_key": SIGNUP_URL,
        "docs": "https://tillacrypto.com/#docs",
        "openapi": API_BASE + "/openapi.json",
        "tools": sorted(TOOL_ROUTES) + ["tilla_about"],
    }


def tilla_status() -> dict:
    """The newest 1-minute bar and the tiers served. No API key needed."""
    return _get("/v1/status", auth=False)


def tilla_tiers() -> dict:
    """The public plans: price, history cap, request limits and size. No API key needed."""
    return _get("/v1/tiers", auth=False)


def tilla_inventory(layer: str | None = None, lane: str | None = None) -> dict:
    """Exactly what the caller's key holds. No arguments: every lane per layer with its series
    count. layer=raw|derived|node and lane=1min|hour|daily|...: every series name there. Call
    this before tilla_latest / tilla_window and use the names it returns. Needs TILLA_API_KEY."""
    return _need_key() or _get("/v1/inventory", auth=True, params={"layer": layer, "lane": lane})


def tilla_window(series=None, layer: str = "raw", lane: str = "1min", start: str | None = None,
                 end: str | None = None, limit: int = 1000, period: str | None = None, markets=None,
                 fields=None) -> dict:
    """A window of bars. Name exactly what you want, one of: `series` = comma-separated names (at most 200) from
    tilla_inventory, or a pattern like 'btc_*' / '*_close'; or `markets` + `fields` ('btc,eth' + 'close,volume' ->
    btc_close, btc_volume, eth_close, eth_volume). layer = raw | derived | node | deep; lane = 1min, 5min, hour,
    daily, ... start/end = 'YYYY-MM-DD[ HH:MM[:SS]]' UTC inclusive, or period = 30d 2m 6m 1y all; no start = the
    newest bars. limit <= 50000. When `more` is true, call again with start = `next_start`. Needs TILLA_API_KEY."""
    miss = _need_key()
    if miss:
        return miss
    if layer not in LAYERS:
        return {"error": "bad_layer", "message": "layer is raw, derived, node or deep"}
    t = _my_tier()
    if isinstance(t, dict):
        return t
    return _get("/v1/%s/%s/%s" % (t, layer, lane), auth=True,
                params={"series": _names(series), "markets": _names(markets), "fields": _names(fields),
                        "start": start, "end": end, "period": period, "limit": int(limit)})


def tilla_latest(series, layer: str = "raw", lane: str = "1min") -> dict:
    """The newest bar of the named series on one lane. Needs TILLA_API_KEY."""
    return tilla_window(series, layer=layer, lane=lane, limit=1)


def tilla_usage() -> dict:
    """The caller's plan and budget right now: tier, history days, limits, used today. Needs TILLA_API_KEY."""
    return _need_key() or _get("/v1/usage", auth=True)


def tilla_markets() -> dict:
    """Every market TILLA carries - crypto, US stocks and ETFs, FX, macro - with its category, its related markets,
    how many series each plan holds of it, and its lanes. No API key needed. Use the `id` with tilla_market."""
    return _get("/v1/markets", auth=False)


def tilla_market(market: str, lane: str = "1min", layer: str = "raw", related: bool = False,
                 period: str | None = None, limit: int = 500) -> dict:
    """One market in one call: every series of `market` (an id from tilla_markets, e.g. btc, nvda, eurusd, gold) the
    key holds on `lane`, on one clock. layer = raw | derived | node | deep | all. related=True adds its connected
    markets (btc: its ETFs and miners). period = 1d 7d 30d 2m 3m 6m 1y 2y 3y all. At most 200 columns an answer:
    `series_next_offset` names the next page. Needs TILLA_API_KEY."""
    miss = _need_key()
    if miss:
        return miss
    t = _my_tier()
    if isinstance(t, dict):
        return t
    return _get("/v1/%s/market/%s" % (t, market), auth=True,
                params={"lane": lane, "layer": layer, "related": "1" if related else None, "period": period,
                        "limit": int(limit)})


def tilla_sample(tier: str = "free") -> dict:
    """The free sample of one plan (free, builder, pro or max), no key needed: how many series it holds on every
    lane, and one aligned 1-minute row of real values. The full one-tick files are at /v1/sample/<tier>.csv and
    .db (named in the answer's `files`)."""
    return _get("/v1/sample/%s" % tier, auth=False)


def tilla_health() -> dict:
    """The newest bar of every lane on every layer - is the data current? No API key needed."""
    return _get("/v1/health", auth=False)


def tilla_docs() -> dict:
    """The whole API manual in one call, no key needed: every call, every parameter, every plan, how paging, tick,
    resume, changes and bulk work. Read this first when you need to know how to do anything."""
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.get(SIGNUP_URL + "/llms-full.txt", headers={"User-Agent": "tilla-mcp/2.0"})
        return {"docs": r.text, "calls": _get("/v1", auth=False)}
    except Exception as e:  # noqa: BLE001
        return {"error": "unreachable", "message": "Could not read the docs (%s)." % type(e).__name__}


def tilla_tick(at: str | None = None, lanes: str | None = None) -> dict:
    """Your whole plan, live, in one call: every series the key holds on every lane that closed at a boundary (`at` =
    'YYYY-MM-DD HH:MM', default the minute just closed). Per lane: bar, complete, series, values. Needs a key."""
    t = _my_tier()
    if isinstance(t, dict):
        return t
    return _get("/v1/%s/tick" % t, auth=True, params={"at": at, "lanes": lanes})


def tilla_changes(since: str) -> dict:
    """Every value our checks repaired since `since` ('YYYY-MM-DD HH:MM:SS') that the key holds, with its value now -
    apply them and a kept copy stays correct. Pass the answer's `until` as the next since. Needs a key."""
    t = _my_tier()
    if isinstance(t, dict):
        return t
    return _get("/v1/%s/changes" % t, auth=True, params={"since": since})


TOOL_ROUTES.update({"tilla_tick": ("GET", "/v1/{tier}/tick"), "tilla_changes": ("GET", "/v1/{tier}/changes")})
TOOL_ROUTES.update({"tilla_markets": ("GET", "/v1/markets"),
                    "tilla_market": ("GET", "/v1/{tier}/market/{subject}"),
                    "tilla_sample": ("GET", "/v1/sample/{name}"),
                    "tilla_health": ("GET", "/v1/health")})
TOOLS = (tilla_about, tilla_status, tilla_tiers, tilla_inventory, tilla_window, tilla_latest, tilla_usage,
         tilla_markets, tilla_market, tilla_sample, tilla_health, tilla_docs, tilla_tick,
         tilla_changes)


# ── MCP registration - only when the server actually runs ─────────────────────
def build():
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("tilla", host=os.environ.get("TILLA_MCP_HOST", "127.0.0.1"),
                  port=int(os.environ.get("TILLA_MCP_PORT", "8971")), instructions=INSTRUCTIONS)
    for fn in TOOLS:
        mcp.tool()(fn)

    @mcp.resource("tilla://about")
    def about_resource() -> str:
        """What TILLA is, for an agent's context."""
        return json.dumps(tilla_about(), indent=2)

    @mcp.resource("tilla://tiers")
    def tiers_resource() -> str:
        """The live plan catalog as JSON."""
        return json.dumps(tilla_tiers(), indent=2)
    return mcp


def main() -> None:
    mcp = build()
    transport = os.environ.get("TILLA_MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio - the default for local agents


if __name__ == "__main__":
    main()
