#!/usr/bin/env python3
"""Refresh data/quotes.json: the latest daily close for every ticker in
trades.json and in cramer.json (the Jim Cramer section).

Yahoo Finance daily bars. Tickers that are not quoted in USD (anything with a
dot suffix, e.g. 000660.KS) are skipped on purpose — the dashboard shows no
gain for those. Exits non-zero if more than a quarter of the tickers fail, so a
broken run is loud rather than silently stale.

Two Yahoo quirks are handled here rather than by hand:
- While the market is open, today's daily bar holds a live price, not a close.
  It is skipped, so a mid-session run keeps the last finished close.
- Yahoo sometimes leaves a finished day's daily close empty (Sandisk, Nov 20,
  2026). That day's close is then taken from the 4:00 PM regular-market price,
  or failing that from the day's last 5-minute bar, instead of silently falling
  back a day.
Any ticker whose close is still older than the rest is listed at the end.
"""
import json, sys, pathlib, datetime, urllib.request, urllib.error
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0"}
NY = ZoneInfo("America/New_York")

def chart(ticker, rng, interval):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={rng}&interval={interval}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as fh:
        return json.load(fh)["chart"]["result"][0]

def latest_close(ticker, prev=None, now=None):
    """prev: this ticker's row from the current quotes.json, if any."""
    now = now or datetime.datetime.now(NY)
    open_now = now.weekday() < 5 and datetime.time(9, 30) <= now.time() < datetime.time(16, 0)
    d = chart(ticker, "5d", "1d")
    ts, close = d["timestamp"], d["indicators"]["quote"][0]["close"]
    days = [datetime.datetime.fromtimestamp(t, NY).date() for t in ts]
    idx = [i for i in range(len(ts)) if not (open_now and days[i] == now.date())]   # finished sessions only
    if not idx:
        raise ValueError("no finished session")
    i = idx[-1]
    if close[i] is not None:
        return round(close[i], 2), days[i].isoformat(), None
    day = days[i]
    m = d.get("meta", {})
    rmt = m.get("regularMarketTime")
    if rmt and m.get("regularMarketPrice") is not None:
        t = datetime.datetime.fromtimestamp(rmt, NY)
        if t.date() == day and t.time() >= datetime.time(16, 0):
            return round(m["regularMarketPrice"], 2), day.isoformat(), "daily close missing; used the 4:00 PM price"
    if prev and prev.get("as_of") == day.isoformat() and prev.get("price") is not None:
        return prev["price"], day.isoformat(), "daily close missing; kept the close already stored for that day"
    try:
        intra = chart(ticker, "5d", "5m")
        q = intra["indicators"]["quote"][0]["close"]
        last = [(datetime.datetime.fromtimestamp(t, NY), c) for t, c in zip(intra["timestamp"], q)
                if c is not None and datetime.datetime.fromtimestamp(t, NY).date() == day]
        auction = [c for t, c in last if t.time() == datetime.time(16, 0)]
        if auction:
            return round(auction[-1], 2), day.isoformat(), "daily close missing; used the 4:00 PM closing bar"
        if last and last[-1][0].time() >= datetime.time(15, 55):
            return round(last[-1][1], 2), day.isoformat(), "daily close missing; used the 3:55 PM bar (approximate, check it)"
    except Exception:
        pass
    j = max(k for k in idx if close[k] is not None)                                   # old behaviour, flagged below
    return round(close[j], 2), days[j].isoformat(), f"daily close for {day} missing; kept {days[j]}"

def tickers_from(path, key="ticker"):
    try:
        return [r[key] for r in json.load(open(path))]
    except FileNotFoundError:
        return []

def main():
    seen, tickers = set(), []
    for tk in tickers_from(ROOT / "data/trades.json") + tickers_from(ROOT / "data/cramer.json"):
        if tk in seen or "." in tk:                     # keep first-seen order, skip non-USD listings
            continue
        seen.add(tk); tickers.append(tk)

    try:
        stored = {q["ticker"]: q for q in json.load(open(ROOT / "data/quotes.json"))}
    except FileNotFoundError:
        stored = {}
    out, failed, notes = [], [], []
    for tk in tickers:
        try:
            price, as_of, note = latest_close(tk, stored.get(tk))
            out.append({"ticker": tk, "price": price, "as_of": as_of})
            if note:
                notes.append(f"{tk}: {note}")
        except Exception as e:
            failed.append(f"{tk} ({type(e).__name__})")

    if failed:
        print("could not quote:", ", ".join(failed), file=sys.stderr)
    if not out or len(failed) > len(tickers) / 4:
        sys.exit(f"too many quote failures ({len(failed)}/{len(tickers)}) — quotes.json left unchanged")

    json.dump(out, open(ROOT / "data/quotes.json", "w"), indent=1)
    days = sorted({r["as_of"] for r in out})
    print(f"quotes.json: {len(out)} tickers, close dated {days[-1]}"
          + (f" ({len(failed)} skipped)" if failed else ""))
    for n in notes:
        print("  note:", n)
    stale = [f"{r['ticker']} {r['as_of']}" for r in out if r["as_of"] != days[-1]]
    if stale:
        print("  older than the rest:", ", ".join(stale))

if __name__ == "__main__":
    main()
