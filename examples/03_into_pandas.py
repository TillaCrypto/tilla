"""A day of BTC and ETH 1-minute closes into a pandas DataFrame, with returns and their correlation.

    pip install pandas
    python examples/03_into_pandas.py
"""
from datetime import datetime, timedelta, timezone

import pandas as pd

from _tilla import get, tier

t = tier()
start = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

rows, cols, nxt = [], None, start
while nxt:                                   # follow next_start until the window is complete
    d = get(f"/v1/{t}/raw/1min", series="btc_close,eth_close", start=nxt, limit=5000)
    cols = cols or ["time"] + d["series"]
    rows += d["data"]
    nxt = d["next_start"] if d["more"] else None

df = pd.DataFrame(rows, columns=cols)
df["time"] = pd.to_datetime(df["time"])
df = df.set_index("time")
ret = df.pct_change().dropna()

print(df.tail())
print(f"\n{len(df)} bars, BTC/ETH 1-minute return correlation over the day: {ret.corr().iloc[0, 1]:.3f}")
