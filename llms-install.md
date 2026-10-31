# Installing the TILLA MCP server (for AI agents such as Cline)

TILLA is read-only market data: crypto, US stocks and ETFs, FX, indices, rates, macro, every BTC/ETH spot ETF fund
and data from a Bitcoin node, on one UTC clock from 1-minute to quarterly. The server only reads from
`https://api.tillacrypto.com` over HTTPS. It places no trades, touches no wallet and writes no files.

## 1. Get a free API key (no account, no card)

```bash
curl -X POST https://api.tillacrypto.com/v1/demo_key
```

The answer is JSON. The `key` field (starts with `tk_live_`) is the API key. Keep it private.

## 2. Add the server to the MCP settings

The server is on PyPI as `tilla-mcp`. With `uv` installed, no other step is needed:

```json
{
  "mcpServers": {
    "tilla": {
      "command": "uvx",
      "args": ["tilla-mcp"],
      "env": {
        "TILLA_API_KEY": "tk_live_YOUR_KEY"
      }
    }
  }
}
```

Without `uv`: run `pip install tilla-mcp`, then use `"command": "tilla-mcp"` and `"args": []`.

## 3. Check it works

Call the `tilla_status` tool. It answers with the API's live status. Then `tilla_tiers` lists the plans and what
the key can read.

## The 14 tools

`tilla_about` · `tilla_status` · `tilla_tiers` · `tilla_inventory` · `tilla_window` · `tilla_latest` · `tilla_usage` ·
`tilla_markets` · `tilla_market` · `tilla_sample` · `tilla_health` · `tilla_docs` · `tilla_tick` · `tilla_changes`

Docs: https://tillacrypto.com/docs · Source: `mcp/tilla_mcp.py` in this repo (MIT).
