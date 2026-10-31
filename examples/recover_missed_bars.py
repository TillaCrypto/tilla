"""Your process was down. Get back every bar you missed, then every value the sources corrected since.

    set TILLA_API_KEY=tk_live_...      (free key: curl -X POST https://api.tillacrypto.com/v1/demo_key)
    python examples/recover_missed_bars.py            keeps bars.db next to it; run it again any time

Standard library only. Two calls do the work:
    GET /v1/<tier>/resume/<layer>/<lane>?since=...&format=csv   every bar after `since`, streamed as CSV
    GET /v1/<tier>/changes?since=...                             every value corrected after `since`
"""
import csv
import io
import sqlite3
import time
import urllib.parse
import urllib.request

from _tilla import BASE, HEADERS, get, key, tier

LANES = [("raw", "1min")]                      # add ("raw", "hour"), ("derived", "1hour") ... as your plan allows
DB = sqlite3.connect("bars.db")
DB.executescript("""
CREATE TABLE IF NOT EXISTS bars (lane TEXT, time TEXT, series TEXT, value REAL, PRIMARY KEY (lane, time, series));
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
""")


def keep(lane, bar_time, cells):
    DB.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?)",
                   [(lane, bar_time, s, v) for s, v in cells.items() if v is not None])


def resume(t):
    """Every bar after the newest one this file holds (a new file starts one hour back)."""
    first = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 3600))
    for layer, lane in LANES:
        name = f"{layer}/{lane}"
        since = DB.execute("SELECT MAX(time) FROM bars WHERE lane=?", (name,)).fetchone()[0] or first
        url = f"{BASE}/v1/{t}/resume/{layer}/{lane}?" + urllib.parse.urlencode({"since": since, "format": "csv"})
        req = urllib.request.Request(url, headers={**HEADERS, "X-API-Key": key()})
        n = 0
        with urllib.request.urlopen(req, timeout=300) as r:
            rows = csv.reader(io.TextIOWrapper(r, encoding="utf-8"))
            head = next(rows)[1:]
            for row in rows:
                if row and row[0]:
                    keep(name, row[0], dict(zip(head, [float(x) if x else None for x in row[1:]])))
                    n += 1
        DB.commit()
        print(f"resume {name}: {n} bar(s) after {since}")


def heal(t):
    """Every value corrected since the last heal, written over the bars this file holds."""
    row = DB.execute("SELECT v FROM meta WHERE k='heal_until'").fetchone()
    since = row[0] if row else time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 7200))
    fixed = 0
    while True:
        d = get(f"/v1/{t}/changes", since=since)
        for name, bars in (d.get("lanes") or {}).items():
            for bar_time, cells in bars.items():
                keep(name, bar_time, cells)
                fixed += len(cells)
        since = d.get("until") or since
        DB.execute("INSERT OR REPLACE INTO meta VALUES ('heal_until', ?)", (since,))
        DB.commit()
        if not d.get("more"):
            break
    print(f"heal: {fixed} corrected value(s) applied")


if __name__ == "__main__":
    t = tier()
    resume(t)
    heal(t)
    total = DB.execute("SELECT COUNT(DISTINCT time) FROM bars").fetchone()[0]
    print(f"bars.db now holds {total} bar(s)")
