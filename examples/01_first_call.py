"""Your first call: the last five 1-minute closes of BTC and ETH.

    python examples/01_first_call.py
"""
from _tilla import get, tier

t = tier()
d = get(f"/v1/{t}/raw/1min", series="btc_close,eth_close", limit=5)

print(f"tier {t} - {d['rows']} bars")
print("time (UTC, bar close)   " + "   ".join(d["series"]))
for row in d["data"]:
    print(row[0], "  ", "   ".join(f"{v:>10}" for v in row[1:]))
