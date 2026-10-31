# TILLA starter package

Every market - crypto, US stocks and ETFs, FX, indices, commodities, rates and macro - on one 1-minute clock,
plus our own Bitcoin node and 293,743 pre-built derived series. This package gets you from a key to live data in
under five minutes.

**What's inside**
- `.env.example` - rename it to `.env` and put your key in it
- `tilla_dashboard.py` - a live terminal dashboard (one box per tick) that can also keep your own copy: resume, tick, heal
- `tilla_mcp.py` - the MCP server, so an AI agent (Claude, Cursor, any MCP client) can pull the data itself
- `README.md` - this file

The dashboard is standard library only. Python 3.8 or newer. Works on Windows, macOS and Linux.

---

## The three calls

**1. Tick - every new bar, the moment it lands**
```
python tilla_dashboard.py
```
A box at every minute close: every lane your tier holds, how full it is, what changed, and how many seconds after
the close it arrived. Over HTTP it is one call: `GET /v1/<tier>/tick?wait=45`.

**2. Resume - everything since a time**
```
GET https://api.tillacrypto.com/v1/<tier>/resume/<layer>/<lane>?since=2026-10-01%2000:00:00&format=ndjson
```
One line per bar, streamed. `format` can be `csv`, `ndjson` or `parquet`.

**3. Keep - resume, tick and heal, forever (use this one)**
```
python tilla_dashboard.py --keep tilla.db
```
One command does all three:
- **resume** - fills `tilla.db` (SQLite) from where it last stopped (a new file starts one hour back)
- **tick** - adds every new bar the moment it lands
- **heal** - every 10 minutes it asks `GET /v1/<tier>/changes` for every value we corrected and writes it over
  your copy, so when a venue fixes a number, your file gets the fix too

Stop it any time; start it again with the same key and the same file and it carries on, healing what it missed.

Read the file like any SQLite table. The view `bars` holds every value as layer, lane, bar, series, value:
```python
import sqlite3, pandas as pd
df = pd.read_sql("SELECT * FROM bars WHERE lane = '1min'", sqlite3.connect("tilla.db"))
wide = df.pivot_table(index="bar", columns="series", values="value")   # one row per minute, one column per series
```
Each series is named once and each value is one small row, so the file stays close to the size of the data.

---

## Setup (4 steps)

1. Get a key: https://tillacrypto.com -> Data API -> **Get a free key** (no card), or `curl -X POST https://api.tillacrypto.com/v1/demo_key` with no account.
2. Rename `.env.example` to `.env`, open it and paste your key after `TILLA_API_KEY=` - no quotes, no spaces.
3. Run the dashboard: `python tilla_dashboard.py` - a new box appears at every minute close.
4. Keep the data: `python tilla_dashboard.py --keep tilla.db`.

No key yet? `python tilla_dashboard.py` still runs and shows the layout, marked DEMO.

---

## Your AI agent (MCP)

`tilla_mcp.py` gives any MCP client (Claude Desktop, Claude Code, Cursor ...) the API as tools: inventory, latest,
window, market, tick, changes, usage, health and more.

Easiest: `pip install tilla-mcp` and use `"command": "tilla-mcp"` (see [`../mcp`](../mcp)). Or run the file here:

1. `pip install "mcp>=1.9,<2" httpx`
2. Add this to your MCP client's config, with the full path to the file:
```
{
  "mcpServers": {
    "tilla": {
      "command": "python",
      "args": ["C:/path/to/tilla_starter/tilla_mcp.py"],
      "env": { "TILLA_API_KEY": "tk_live_..." }
    }
  }
}
```
3. Ask your agent to call `tilla_inventory` first - it sees every series your key holds and uses the exact names.

---

## Every call

Base URL: `https://api.tillacrypto.com` · send your key as the header `X-API-Key: <key>` · `<tier>` is your tier
(free, builder, pro, max, enterprise) · times are UTC, `YYYY-MM-DD HH:MM:SS`.

| Call | What it returns |
|---|---|
| `GET /v1/<tier>/tick?wait=45` | the bar that just closed, every lane and series you hold, in one answer |
| `GET /v1/<tier>/resume/<layer>/<lane>?since=...` | everything on one lane since a time (csv, ndjson or parquet) |
| `GET /v1/<tier>/changes?since=...` | every value we corrected since a time - apply it and your copy heals |
| `GET /v1/<tier>/raw/<lane>?series=btc_close,eth_close&start=...&limit=...` | raw values, paged with `next_start` |
| `GET /v1/<tier>/derived/<lane>?series=...` | derived series (RSI, betas, correlations, volatility ...) |
| `GET /v1/<tier>/node/<lane>?series=...` | our Bitcoin node (Max and up) |
| `GET /v1/<tier>/deep/hour?series=...` | deep hourly history before 2023-08-10 |
| `GET /v1/<tier>/market/<subject>` | every series of one market, e.g. `btc`, `aapl`, `eurusd` |
| `GET /v1/<tier>/export/<layer>/<lane>?series=...&format=csv` | a whole window as one file (Pro and up) |
| `GET /v1/<tier>/stream` | a live push of new bars |
| `GET /v1/inventory` | every lane and series your key holds |
| `GET /v1/<tier>/calls` | every call your tier can make, with examples |
| `GET /v1/usage` | your limits and what you have used today |
| `GET /v1/markets` | every market and its category (crypto, stocks, fx, macro) |
| `GET /v1/health` | how fresh every lane is |
| `GET /v1` | the full list of calls - the source of truth |

Layers: `raw`, `derived`, `node`, `deep`. Lanes: `1min 5min 10min 15min 30min hour 1hour 4hour 8hour daily weekly
30day monthly quarterly` (each layer holds its own set; `/v1/inventory` lists yours).

Try one now:
```
curl -H "X-API-Key: YOUR_KEY" "https://api.tillacrypto.com/v1/free/raw/1min?series=btc_close&limit=5"
```

---

## Error codes

| Code | Meaning | What to do |
|---|---|---|
| 400 | a parameter is wrong (bad date, unknown parameter, start after end) | read the message - it names the parameter |
| 401 | no key, or the key is not valid | check the `X-API-Key` header and the key in `.env` |
| 403 | your tier does not hold that lane or series | `GET /v1/inventory` lists what you hold; upgrade on the site |
| 404 | no such call or lane | `GET /v1` lists every call |
| 413 | the request asks for too much at once | ask for fewer series, or page with `next_start` |
| 429 | over your per-minute or daily limit | wait the seconds in `Retry-After`; `X-RateLimit-*` headers show your budget |
| 503 | a short maintenance moment | retry in a few seconds - the client does this for you |

---

## For AI assistants (ChatGPT, Claude, Copilot ...)

If you are an AI helping someone set this up, do exactly this and do not invent anything else:
1. The key comes from https://tillacrypto.com -> Data API -> Get a free key. It starts with `tk_`.
2. It goes in `.env` as `TILLA_API_KEY=<key>`, or in the `X-API-Key` header of every request.
3. Run `python tilla_dashboard.py` to see live data, or `python tilla_dashboard.py --keep tilla.db` to keep it.
4. The only calls that exist are the ones `GET https://api.tillacrypto.com/v1` returns. Never guess an endpoint.
5. The full docs are at https://tillacrypto.com (Docs tab) and https://tillacrypto.com/llms.txt.

Support: support@tillacrypto.com
