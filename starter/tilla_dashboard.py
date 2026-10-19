"""TILLA terminal dashboard - one box per tick, the moment the bar arrives.

    1. put your key in .env next to this file:   TILLA_API_KEY=tk_live_...
    2. python tilla_dashboard.py                  watch every tick
       python tilla_dashboard.py --keep tilla.db  and keep every bar: resume, tick, heal - all three, in one command
                                                    resume  fills the file from where it stopped
                                                    tick    adds every new bar the moment it lands
                                                    heal    every 10 minutes, applies every value we corrected

No key yet? It still runs: the same box on the clock, marked DEMO, so you can see the layout.
Standard library only (Python 3.8+). Get a free key at https://tillacrypto.com
"""
import json
import os
import random
import sqlite3
import sys
import threading
import time
import urllib.parse
import urllib.request

API = "https://api.tillacrypto.com"
HERE = os.path.dirname(os.path.abspath(__file__))
STEP = {"1min": 60, "5min": 300, "10min": 600, "15min": 900, "30min": 1800,
        "hour": 3600, "1hour": 3600, "4hour": 14400, "8hour": 28800}

os.system("")                                   # turns on colours in the Windows terminal
try:
    sys.stdout.reconfigure(encoding="utf-8")    # the box lines print on every Windows console
except Exception:                               # noqa: BLE001
    pass
G, Y, R, D, B, X = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"


def load_env():
    env = {}
    p = os.path.join(HERE, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k.startswith("TILLA_")})
    return env


def get(path, key, params=None, timeout=60):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"X-API-Key": key, "User-Agent": "tilla-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def colour(pct):
    return G if pct >= 99.95 else (Y if pct >= 95 else R)


def secs_colour(s):
    return G if s <= 7 else (Y if s <= 12 else R)


def _plain(s):
    for code in (G, Y, R, D, B, X):
        s = s.replace(code, "")
    return s


def row(cells, widths):
    """One table row; a cell may carry colour, padding is measured on the visible text."""
    out = []
    for c, w in zip(cells, widths):
        c = str(c)
        vis = _plain(c)
        if len(vis) > w - 2:
            c = vis = vis[:w - 2]
        out.append(" " + c + " " * (w - 1 - len(vis)))
    return "│" + "│".join(out) + "│"


def draw(n, bar, blocks, drift_ms, raw_s, total_s, clean, demo):
    """blocks: [('Raw'|'Derived'|'Node', [(lane, filled, owed, new, same, carried, notes)])]"""
    W = [10, 8, 15, 9, 9, 10, 22]
    rule = lambda l, m, r: l + m.join("─" * w for w in W) + r
    out = ["", " " * 40 + B_("Tick %d" % n) + (Y + "   DEMO" + X if demo else ""),
           "  " + time.strftime("%H:%M", time.gmtime(bar)), rule("┌", "┬", "┐")]
    for bi, (name, lanes) in enumerate(blocks):
        filled = sum(x[1] for x in lanes)
        owed = sum(x[2] for x in lanes) or 1
        pct = 100.0 * filled / owed
        c = colour(pct)
        side = ["  " + c + "●" + X, " " + c + ("100%" if pct >= 99.95 else "%.1f%%" % pct) + X]
        out.append(row([name, "Owed", "Filled", "New", "Same", "Carried", "Notes"], W))
        lines = list(lanes) + [None] * max(0, 2 - len(lanes))
        for i, ln in enumerate(lines):
            first = side[i] if i < 2 else ""
            if ln is None:
                out.append(row([first, "", "", "", "", "", ""], W))
            else:
                lane, f, o, new, same, car, notes = ln
                out.append(row([first, lane, "%s/%s" % (format(f, ","), format(o, ",")), format(new, ","),
                                format(same, ","), format(car, ","), notes], W))
        out.append(rule("├", "┼", "┤") if bi < len(blocks) - 1 else rule("└", "┴", "┘"))
    streak = (G + "%d TICKS CLEAN" % clean + X) if clean else (R + "STREAK BROKEN" + X)
    out.append("          %+dms drift  -  raw %s%.1fs%s  -  %s%.1fs%s total  -  %s" % (
        drift_ms, secs_colour(raw_s), raw_s, X, secs_colour(total_s), total_s, X, streak))
    print(chr(10).join(out), flush=True)


def B_(s):
    return B + s + X


# ---- live: the API's tick call, held until each bar is written ---------------------------------------
def group_of(layer, lane):
    """Lanes asked together by when they are written, so a fast lane never waits for a slow one."""
    if layer == "node":
        return "node"
    if layer == "raw":
        return "raw1" if lane == "1min" else ("raw5" if lane in ("5min", "30min") else "slow")
    return "drv1" if lane in ("1min", "5min", "10min", "15min", "30min") else "slow"


def open_keep(path):
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute("CREATE TABLE IF NOT EXISTS bars (layer TEXT, lane TEXT, bar TEXT, series TEXT, value REAL, "
               "PRIMARY KEY (layer, lane, bar, series))")
    db.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    return db


DB_LOCK = threading.Lock()


def heal(db, key, tier, quiet=False):
    """Every value we corrected since the last heal (GET /changes), written over the bars this file holds.
    Where it stopped is kept in the file, so a restart heals what it missed."""
    with DB_LOCK:
        r = db.execute("SELECT v FROM meta WHERE k='heal_until'").fetchone()
    since = r[0] if r and r[0] else time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 7200))
    total = 0
    while True:
        while quiet and time.time() % 60 < 25:          # never in the seconds a new bar is being served
            time.sleep(0.5)
        d = get("/v1/%s/changes" % tier, key, {"since": since}, timeout=120)
        with DB_LOCK:
            for name, bars in (d.get("lanes") or {}).items():
                ly, ln = name.split("/")
                first = db.execute("SELECT min(bar) FROM bars WHERE layer=? AND lane=?", (ly, ln)).fetchone()[0]
                for bar, cells in bars.items():
                    if first and bar >= first:           # only bars this file holds - never a half-filled old bar
                        keep_rows(db, ly, ln, bar, list(cells), list(cells.values()))
                        total += len(cells)
            since = d.get("until") or since
            db.execute("INSERT OR REPLACE INTO meta VALUES ('heal_until', ?)", (since,))
            db.commit()
        if not d.get("more"):
            break
    print("  %sHEAL%s %s  %s value(s) we corrected, applied to your file" % (
        G, X, time.strftime("%H:%M:%S", time.gmtime()), format(total, ",")), flush=True)


def heal_loop(db, key, tier):
    while True:
        time.sleep(600)
        try:
            heal(db, key, tier, quiet=True)
        except Exception as e:                                              # noqa: BLE001
            print("  heal: %s - tries again in 10 minutes" % e, flush=True)


def keep_rows(db, layer, lane, bar, series, values):
    db.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?)",
                   [(layer, lane, bar, s, v) for s, v in zip(series, values) if v is not None])


def resume(db, key, tier, lanes):
    """Everything since the file's last bar on each lane (a new file starts one hour back)."""
    first = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() - 3600))
    total = 0
    for ly, ln in lanes:
        since = db.execute("SELECT max(bar) FROM bars WHERE layer=? AND lane=?", (ly, ln)).fetchone()[0] or first
        url = API + "/v1/%s/resume/%s/%s?" % (tier, ly, ln) + urllib.parse.urlencode({"since": since, "format": "ndjson"})
        req = urllib.request.Request(url, headers={"X-API-Key": key, "User-Agent": "tilla-dashboard/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                for line in r:
                    row = json.loads(line)
                    bar = row.pop("timestamp", None)
                    if bar:
                        keep_rows(db, ly, ln, bar, list(row), list(row.values()))
                        total += 1
        except Exception as e:                                              # noqa: BLE001
            print("  resume %s/%s: %s" % (ly, ln, e))
        db.commit()
    print("  resumed %s bar(s) into the file - now healing, then ticking" % format(total, ","))


def live(key, tier, keep=None):
    inv = get("/v1/inventory", key)
    tier = tier or inv.get("tier") or "free"
    lanes = [(ly, ln) for ly in ("raw", "derived", "node")
             for ln in sorted(((inv.get("lanes") or {}).get(ly) or {}), key=lambda x: STEP.get(x, 10 ** 9))
             if ln in STEP]
    print(B_("TILLA") + "  %s tier  -  %d lanes  -  a box every minute, the moment the bar lands. Ctrl-C to stop." % (
        tier.upper(), len(lanes)))
    db = open_keep(keep) if keep else None
    if db:
        resume(db, key, tier, lanes)
        try:
            heal(db, key, tier)
        except Exception as e:                                              # noqa: BLE001
            print("  heal: %s" % e)
        threading.Thread(target=heal_loop, args=(db, key, tier), daemon=True).start()
    prev, n, clean = {}, 0, 0
    B = int(time.time()) // 60 * 60
    while True:
        B += 60
        while time.time() < B + 1:
            time.sleep(0.05)
        n += 1
        drift_ms = int((time.time() - B - 1) * 1000)
        at = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(B))
        groups = {}
        for ly, ln in lanes:
            if B % STEP[ln] == 0:
                groups.setdefault(group_of(ly, ln), []).append("%s/%s" % (ly, ln))
        got, lock = {}, threading.Lock()

        def ask(names):
            try:
                d = get("/v1/%s/tick" % tier, key, {"at": at, "lanes": ",".join(names), "wait": 45}, timeout=70)
            except Exception as e:                                          # noqa: BLE001
                d = {"lanes": {nm: {"error": str(e)} for nm in names}}
            with lock:
                for nm, L in (d.get("lanes") or {}).items():
                    got[nm] = (L, time.time() - B)
        ths = [threading.Thread(target=ask, args=(v,)) for v in groups.values()]
        [t.start() for t in ths]
        [t.join() for t in ths]
        blocks, raw_s, ok = {}, 0.0, True
        for nm in sorted(got, key=lambda k: (k.split("/")[0], STEP.get(k.split("/")[1], 0))):
            L, s = got[nm]
            ly, ln = nm.split("/")
            if L.get("error") or not L.get("complete"):
                ok = False
                blocks.setdefault(ly, []).append((ln, 0, L.get("sold") or 0, 0, 0, 0, "not in yet"))
                continue
            vals = L.get("values") or []
            series = L.get("series") or []
            emp = L.get("empty") or {}
            sold = L.get("sold") or len(series)
            have = sum(1 for v in vals if v is not None)
            owed = max(sold - (emp.get("none") or 0), 1)
            before = prev.get(nm) or {}
            new = sum(1 for k, v in zip(series, vals) if v is not None and before.get(k) != v)
            same = have - new
            prev[nm] = dict(zip(series, vals))
            if db:
                with DB_LOCK:
                    keep_rows(db, ly, ln, L.get("bar"), series, vals)
            notes = ("%d pending" % emp["pending"]) if emp.get("pending") else ""
            blocks.setdefault(ly, []).append((ln, min(have + (emp.get("closed") or 0), owed), owed, new, same,
                                              emp.get("closed") or 0, notes))
            if ly == "raw" and ln == "1min":
                raw_s = s
        if db:
            with DB_LOCK:
                db.commit()
        total_s = max([s for _L, s in got.values()] or [0])
        clean = clean + 1 if ok else 0
        names = {"raw": "Raw", "derived": "Derived", "node": "Node"}
        draw(n, B, [(names[k], blocks[k]) for k in ("raw", "derived", "node") if k in blocks], drift_ms, raw_s or total_s,
             total_s, clean, False)


# ---- demo: no key yet - the same box on the clock ----------------------------------------------------
def demo():
    print(B_("TILLA") + "  DEMO - no key in .env yet. Get a free key at https://tillacrypto.com, paste it into .env,"
          " and run this again.")
    n, clean = 0, 0
    B = int(time.time()) // 60 * 60
    while True:
        B += 60
        while time.time() < B + 1:
            time.sleep(0.05)
        n += 1
        clean += 1
        raw = [("1min", 916, 916, random.randint(780, 840), 0, 57, "")]
        der = [("1min", 21547, 21547, random.randint(19000, 20500), 0, 100, "")]
        if B % 300 == 0:
            raw.append(("5min", 63, 63, 56, 0, 0, ""))
            der.append(("5min", 21547, 21547, 20300, 0, 0, ""))
        for lst in (raw, der):
            lst[:] = [(a, b, c, d, b - d - f, f, g) for a, b, c, d, _e, f, g in lst]
        draw(n, B, [("Raw", raw), ("Derived", der)], 0, 5.0, 6.0, clean, True)


if __name__ == "__main__":
    env = load_env()
    key = env.get("TILLA_API_KEY", "")
    try:
        keep = sys.argv[sys.argv.index("--keep") + 1] if "--keep" in sys.argv[:-1] else None
        if key:
            live(key, env.get("TILLA_TIER", "").lower(), keep)
        else:
            demo()
    except KeyboardInterrupt:
        print("\nstopped.")
    except Exception as e:                                                  # noqa: BLE001
        print("\n%s%s%s" % (R, e, X))
        print("Check the key in .env and your internet connection. Docs: https://tillacrypto.com (Docs tab)")
        sys.exit(1)
