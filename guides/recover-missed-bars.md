# Your bot was down for an hour. Here is how to get every bar back - and the corrections

*By Colbie Kelley, who builds TILLA. The code is MIT and uses TILLA's free plan.*

Every system that keeps its own copy of market data eventually goes down: a deploy, a crash, a laptop lid, a lost
connection. When it comes back, two things are wrong, and most pipelines only fix the first:

1. **Bars are missing** for the time it was away.
2. **Some bars it already holds are now wrong**, because a source corrected a value after it was first published
   (a late print, a restated macro number, an exchange fixing a bad candle).

A backfill fixes (1). Nothing in a typical setup fixes (2), so a backtest quietly trains on numbers the source itself
withdrew.

## The two calls

TILLA serves every market (crypto, US stocks, FX, macro, BTC/ETH spot ETF flows, Bitcoin node data) on one UTC clock,
and every bar is labelled by its close. Recovery is two calls:

```
GET /v1/<tier>/resume/<layer>/<lane>?since=<your newest bar>&format=csv
GET /v1/<tier>/changes?since=<your last heal>
```

`resume` streams every bar after the one you hold. `changes` returns every value corrected after a time, grouped by
lane and bar, with an `until` cursor and a `more` flag - so you page until `more` is false and store `until` for next
time.

## The code

The full script is [`examples/recover_missed_bars.py`](../examples/recover_missed_bars.py) (standard library only).
The two halves:

```python
def resume(t):
    since = newest_bar_in_file() or one_hour_ago()
    url = f"{BASE}/v1/{t}/resume/raw/1min?" + urlencode({"since": since, "format": "csv"})
    with urlopen(Request(url, headers={"X-API-Key": KEY})) as r:
        rows = csv.reader(io.TextIOWrapper(r, encoding="utf-8"))
        head = next(rows)[1:]                      # series names come once, in the header
        for row in rows:
            keep("raw/1min", row[0], dict(zip(head, [float(x) if x else None for x in row[1:]])))

def heal(t):
    since = stored_heal_cursor() or two_hours_ago()
    while True:
        d = get(f"/v1/{t}/changes", since=since)
        for lane, bars in d["lanes"].items():
            for bar_time, cells in bars.items():
                keep(lane, bar_time, cells)        # overwrite: the corrected value wins
        since = d["until"]
        store_heal_cursor(since)
        if not d["more"]:
            break
```

Run it after any restart. Run it twice and nothing changes: both halves start from what the file already holds.

## Three details that matter

- **Empty means empty.** A value the source never published comes back empty, never forward-filled. Only a closed
  market (a weekend, a holiday) is carried.
- **One clock.** Because every lane is labelled by bar close in UTC, the bars you recover join row for row with what
  you already had - no resampling and no timezone fixes.
- **The cursor lives in your file.** Keep `until` where the data is, so a crash between the two calls loses nothing.

## Try it

```bash
curl -X POST https://api.tillacrypto.com/v1/demo_key      # a free key, no account
export TILLA_API_KEY=tk_live_...
python examples/recover_missed_bars.py
```

The free plan holds BTC, ETH and a set of macro series with 30 days of history. Paid plans add more markets, more
clocks and indicators computed with no look-ahead: https://tillacrypto.com/pricing

*Disclosure: I build TILLA. Questions: https://tillacrypto.com/contact*
