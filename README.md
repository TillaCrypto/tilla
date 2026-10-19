<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/tilla-logo-white.png">
    <img src="assets/tilla-logo.png" alt="TILLA" width="120">
  </picture>
</p>

# TILLA

Market data for people building trading models, bots and AI agents: crypto, US stocks and ETFs, FX, indices,
commodities, rates and macro on one 1-minute clock, plus data from a Bitcoin node I run myself.

This repo is everything you need to start, free: a live terminal dashboard that keeps a local copy of the data in
sync, an MCP server so your AI agent can pull the data itself, and three short examples.

Site: https://tillacrypto.com · Docs: https://tillacrypto.com/docs · X: [@TillaCryptoHub](https://x.com/TillaCryptoHub)

## Get a free key (no account, no card)

```
curl -X POST https://api.tillacrypto.com/v1/demo_key
```

Or sign up at https://tillacrypto.com for a free key tied to your account.

## Your first call

```
curl -H "X-API-Key: tk_live_YOUR_KEY" "https://api.tillacrypto.com/v1/free/raw/1min?series=btc_close,eth_close&limit=5"
```

Every bar is labelled by its close, in UTC. A value a source never published stays empty; nothing is guessed.

## What's in here

| Folder | What it does |
|---|---|
| [`starter/`](starter) | `tilla_dashboard.py` - one command keeps a SQLite copy current: **resume** what you missed, **tick** every new bar, **heal** values a source corrected later. Standard library only. |
| [`mcp/`](mcp) | `tilla_mcp.py` - the MCP server for Claude, Cursor or any MCP client |
| [`examples/`](examples) | three short scripts: your first call, every coin's close in one call, a day of data into pandas |

```
cd starter
python tilla_dashboard.py --keep tilla.db
```

## The three calls the dashboard is built on

- **Tick** - `GET /v1/<tier>/tick` - every series your plan holds for the bar that just closed, in one answer
- **Resume** - `GET /v1/<tier>/resume/<layer>/<lane>?since=...` - every bar since you stopped, streamed
- **Heal** - `GET /v1/<tier>/changes?since=...` - every value corrected since a time, so your copy gets the fix

## Plans

Free forever with no card. Paid plans add more markets, more history and more clocks: https://tillacrypto.com/pricing

## Questions

I answer every message myself: https://tillacrypto.com/contact, or a DM on X. Issues on this repo are welcome too.
