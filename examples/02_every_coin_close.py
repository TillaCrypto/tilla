"""One word for a whole category: the newest close of every coin your plan holds.

    python examples/02_every_coin_close.py
    python examples/02_every_coin_close.py stocks      (or fx, macro)
"""
import sys

from _tilla import get, tier

category = sys.argv[1] if len(sys.argv) > 1 else "crypto"
t = tier()
d = get(f"/v1/{t}/raw/1min", markets=category, fields="close", limit=1)

if not d["data"]:
    raise SystemExit("no bar yet - try again in a minute")
bar = d["data"][-1]
print(f"{category} closes at {bar[0]} UTC ({len(d['series'])} markets on the {t} plan)")
for name, value in zip(d["series"], bar[1:]):
    print(f"  {name:<18} {value}")
