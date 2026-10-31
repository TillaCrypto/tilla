# TILLA MCP server

**Let your AI agent pull TILLA's market data directly.**

[TILLA](https://tillacrypto.com) serves raw venue data, derived indicators computed from it bar by bar
with no look-ahead, and blocks and mempool data from our own Bitcoin node - crypto spot and derivatives,
equities and ETFs, FX, rates and macro - every value on one UTC clock, every bar hashed as it lands.

This is the official [Model Context Protocol](https://modelcontextprotocol.io) server. Add it to any MCP
client and your agent can query TILLA on its own.

## Connect in 30 seconds

1. **Get a free API key** at **https://tillacrypto.com** (no card), or `POST https://api.tillacrypto.com/v1/demo_key`
   for one with no account.
2. Add the server to your MCP client.

### Claude Desktop / Claude Code / Cursor (local, stdio)

First `pip install "mcp>=1.2,<2" httpx`, then point your client at `tilla_mcp.py` in this folder:

```jsonc
{
  "mcpServers": {
    "tilla": {
      "command": "python",
      "args": ["/path/to/tilla_mcp.py"],
      "env": { "TILLA_API_KEY": "tk_live_your_key_here" }
    }
  }
}
```

Or install it from PyPI (`pip install tilla-mcp`) and use `"command": "tilla-mcp"` - or with uv, nothing to install: `"command": "uvx", "args": ["tilla-mcp"]`.
### Remote / hosted (streamable HTTP)

```bash
TILLA_MCP_TRANSPORT=http TILLA_API_KEY=tk_live_... python tilla_mcp.py
# serves MCP over http://127.0.0.1:8971/mcp  (front with TLS for a public connector)
```

## Tools

Every tool calls a real route of the API (`TOOL_ROUTES` in `tilla_mcp.py` names it).

| Tool | Key? | What it does | API call |
|---|---|---|---|
| `tilla_about` | no | What TILLA is and how to start | - |
| `tilla_status` | no | The newest 1-minute bar and the tiers served | `GET /v1/status` |
| `tilla_tiers` | no | The public plans: price, history cap, limits, size | `GET /v1/tiers` |
| `tilla_inventory` | yes | Exactly which series the key holds, per layer and lane (call this first) | `GET /v1/inventory` |
| `tilla_latest` | yes | The newest bar of named series on one lane | `GET /v1/<tier>/<layer>/<lane>` |
| `tilla_window` | yes | A range of bars; page with `next_start` while `more` is true | `GET /v1/<tier>/<layer>/<lane>` |
| `tilla_usage` | yes | The key's plan and budget right now | `GET /v1/usage` |
| `tilla_markets` | no | Every market, its category and related markets | `GET /v1/markets` |
| `tilla_market` | yes | One market (and optionally its related ones) on one clock | `GET /v1/<tier>/market/<id>` |
| `tilla_sample` | no | The free sample of a plan: series per lane + one real row | `GET /v1/sample/<tier>` |
| `tilla_health` | no | The newest bar of every lane - is the data current | `GET /v1/health` |
| `tilla_docs` | no | The whole API manual in one call | `GET /llms-full.txt` + `GET /v1` |
| `tilla_tick` | yes | Every series the key holds for the bar that just closed, one call | `GET /v1/<tier>/tick` |
| `tilla_changes` | yes | Every value repaired since a time, so a kept copy stays correct | `GET /v1/<tier>/changes` |

Resources: `tilla://about`, `tilla://tiers`.

## Config (env)

| Var | Default | Meaning |
|---|---|---|
| `TILLA_API_KEY` | - | Your `tk_live_...` key (needed for keyed tools) |
| `TILLA_API_BASE` | `https://api.tillacrypto.com` | API base (dev: `http://127.0.0.1:8898`) |
| `TILLA_MCP_TRANSPORT` | `stdio` | `stdio` (local) or `http` (remote) |
| `TILLA_MCP_HOST` / `TILLA_MCP_PORT` | `127.0.0.1` / `8971` | HTTP bind |

## Safe by design

- **Read-only:** every tool is an HTTPS `GET` to `api.tillacrypto.com` (or `tillacrypto.com` for the docs). No tool
  writes a file, runs a command, places a trade or touches a wallet.
- **Your key** is read from `TILLA_API_KEY` and sent only to the TILLA API, never logged or returned to the agent.
- **HTTP mode binds to `127.0.0.1`** unless you set `TILLA_MCP_HOST` yourself.
- **Two dependencies,** both standard: the official `mcp` SDK and `httpx`.

## Notes for the agent

- Call `tilla_inventory` before naming a series - **never guess a series name**.
- A window with no `start` returns the newest bars; with a `start`, page forward with `next_start` until
  `more` is false.
- `403` means the key or the data is outside the plan; `429` means a minute or day budget was hit, and
  `retry_after_seconds` says when to try again.
- An empty value is real: a closed market carries its last print, but an open market with no print (and a
  derived value with no mathematical answer) is left empty, never invented.

MIT licensed. Data access governed by the TILLA plan terms.

<!-- mcp-name: io.github.TillaCrypto/tilla-mcp -->
