"""TILLA market data as LangChain tools, so any LangChain agent can read prices, macro and history.

    pip install langchain-core
    set TILLA_API_KEY=tk_live_...      (free key: curl -X POST https://api.tillacrypto.com/v1/demo_key)
    python examples/langchain_tools.py

Pass the tools to any agent, e.g. `create_react_agent(model, TILLA_TOOLS)`.
"""
from langchain_core.tools import tool

from _tilla import get, tier


@tool
def tilla_latest(category: str = "crypto") -> dict:
    """Newest bar-close prices for a whole market category on TILLA's 1-minute clock.
    category: one of crypto, stocks, fx, macro. Returns {"time": UTC bar close, "closes": {series: value}}."""
    d = get(f"/v1/{tier()}/raw/1min", markets=category, fields="close", limit=1)
    if not d["data"]:
        return {"time": None, "closes": {}}
    bar = d["data"][-1]
    return {"time": bar[0], "closes": dict(zip(d["series"], bar[1:]))}


@tool
def tilla_history(series: str, lane: str = "hour", limit: int = 48) -> dict:
    """Recent history of one or more TILLA series on one clock.
    series: comma-separated names, e.g. "btc_close,eth_close". lane: 1min, 5min, 10min, 30min, hour, daily,
    weekly, monthly or quarterly. limit: number of bars (max 5000). Returns {"series": [...], "rows": [[time, ...]]}."""
    d = get(f"/v1/{tier()}/raw/{lane}", series=series, limit=min(int(limit), 5000))
    return {"series": d["series"], "rows": d["data"][-int(limit):]}


TILLA_TOOLS = [tilla_latest, tilla_history]

if __name__ == "__main__":
    print(tilla_latest.invoke({"category": "crypto"}))
    print(tilla_history.invoke({"series": "btc_close,eth_close", "lane": "hour", "limit": 3}))
