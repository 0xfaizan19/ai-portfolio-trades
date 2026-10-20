#!/usr/bin/env python3
"""Refresh data/quotes.json: the latest daily close for every ticker in trades.json.

Yahoo Finance daily bars. Tickers that are not quoted in USD (anything with a
dot suffix, e.g. 000660.KS) are skipped on purpose — the dashboard shows no
gain for those. Exits non-zero if more than a quarter of the tickers fail, so a
broken run is loud rather than silently stale.
"""
import json, sys, pathlib, datetime, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0"}

def latest_close(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as fh:
        d = json.load(fh)["chart"]["result"][0]
    ts, close = d["timestamp"], d["indicators"]["quote"][0]["close"]
    i = max(j for j, v in enumerate(close) if v is not None)
    return round(close[i], 2), datetime.datetime.fromtimestamp(ts[i], datetime.UTC).strftime("%Y-%m-%d")

def main():
    trades = json.load(open(ROOT / "data/trades.json"))
    seen, tickers = set(), []
    for t in trades:                      # keep first-seen order, skip non-USD listings
        tk = t["ticker"]
        if tk in seen or "." in tk:
            continue
        seen.add(tk); tickers.append(tk)

    out, failed = [], []
    for tk in tickers:
        try:
            price, as_of = latest_close(tk)
            out.append({"ticker": tk, "price": price, "as_of": as_of})
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

if __name__ == "__main__":
    main()
