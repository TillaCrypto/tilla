<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/tilla-logo-white.png">
    <img src="assets/tilla-logo.png" alt="TILLA" width="120">
  </picture>
</p>

# TILLA

Market data for trading models, bots and AI agents. Crypto, US stocks and ETFs, FX, rates and macro on **one UTC
clock**, from 1-minute bars to quarterly.

- **Every market lines up.** BTC, NVDA, EUR/USD, the 10-year yield and VIX share the same timestamp. No joins, no drift.
- **Bitcoin and Ether spot ETF flows, fund by fund**, daily, next to price, funding and open interest.
- **293,743 derived indicators**, computed bar by bar with no look-ahead.
- **Our own Bitcoin node**: blocks, mempool and fees on the same clock as the market.
- **Your copy never breaks.** Go offline and one call refills every missed bar; a second call delivers every value a
  source corrected later.
- **History**: hourly crypto from 2017, FX from 2002.

Site: https://tillacrypto.com · Docs: https://tillacrypto.com/docs · Plans: https://tillacrypto.com/pricing

## In your AI agent (MCP)

```
pip install tilla-mcp
```

```jsonc
{
  "mcpServers": {
    "tilla": {
      "command": "tilla-mcp",
      "env": { "TILLA_API_KEY": "tk_live_your_key_here" }
    }
  }
}
```

With [uv](https://docs.astral.sh/uv/) there is nothing to install: `"command": "uvx", "args": ["tilla-mcp"]`.

14 tools for Claude, Cursor or any MCP client: latest bars, history, one whole market at a time, the live tick,
corrections and plans. Ask things like *"BTC price against spot ETF flows this month"* or *"NVDA and BTC on one
hourly chart"*. Tool list: [`mcp/README.md`](mcp/README.md).

<a href="https://glama.ai/mcp/servers/TillaCrypto/tilla"><img width="380" src="https://glama.ai/mcp/servers/TillaCrypto/tilla/badge" alt="TILLA MCP server on Glama" /></a>

## A key and a first call

A free key, no account and no card:

```
curl -X POST https://api.tillacrypto.com/v1/demo_key
```

```
curl -H "X-API-Key: tk_live_YOUR_KEY" "https://api.tillacrypto.com/v1/free/raw/1min?series=btc_close,eth_close&limit=5"
```

Every bar is labelled by its close, in UTC. A value a source never published stays empty; nothing is guessed.
JSON, CSV, NDJSON or Parquet (`format=`). A [Postman collection](postman) has every call ready to run.

## What's in here

| Folder | What it is |
|---|---|
| [`starter/`](starter) | `tilla_dashboard.py`: a live terminal dashboard that keeps a SQLite copy current - **resume** what you missed, **tick** every new bar, **heal** what a source corrected. Standard library only. |
| [`mcp/`](mcp) | `tilla_mcp.py`: the MCP server (also `pip install tilla-mcp`) |
| [`examples/`](examples) | a first call, every coin's close in one call, a day of data in pandas, `one_clock.ipynb` (30 days of crypto and macro on one clock, free plan), `langchain_tools.py` (TILLA as LangChain tools) and `n8n_tilla_workflow.json` (import into n8n) |
| [`postman/`](postman) | the API as a Postman collection; Insomnia and other clients import `https://api.tillacrypto.com/openapi.json` |

```
cd starter
python tilla_dashboard.py --keep tilla.db
```

## The three calls behind it

- **Tick** - `GET /v1/<tier>/tick` - every series your plan holds for the bar that just closed, in one answer
- **Resume** - `GET /v1/<tier>/resume/<layer>/<lane>?since=...` - every bar since you stopped, streamed
- **Changes** - `GET /v1/<tier>/changes?since=...` - every value corrected since a time, so your copy gets the fix

## Safe to run

Everything here only reads market data from `api.tillacrypto.com` over HTTPS. Nothing trades, touches a wallet or
reads your other files. Your key stays in your own `.env` or environment and goes only to the TILLA API. The only
thing written is the SQLite file you name with `--keep`.

## License

The code is MIT ([LICENSE](LICENSE)). The data you pull with it is covered by your TILLA plan:
https://tillacrypto.com/docs

## Contact

I answer every message myself: https://tillacrypto.com/contact, [@TillaCryptoHub](https://x.com/TillaCryptoHub) on X,
or an issue on this repo.
