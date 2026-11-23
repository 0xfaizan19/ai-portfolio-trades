#!/usr/bin/env python3
"""Jim Cramer tracker: screenshots, prices and the resume point.

    python3 cramer.py show
        Where the last Cramer scan got to, and how far back the next one must look.

    python3 cramer.py shot POST_ID PART1.png [PART2.png]
        Turns a saved screenshot of one post into cramer/POST_ID.webp. A second
        part (a tall post captured in two pieces) is stacked under the first.

    python3 cramer.py prices
        Fills price_then for rows that don't have one yet (the price when he
        posted, see price_at below) and rebuilds data/cramer_stocks.json: name,
        exchange, 52-week range and about three months of daily closes per ticker.

    python3 cramer.py check
        Sanity checks: required fields, stances, screenshots on disk, company rows.

    python3 cramer.py record --status ok --newest-post-id ID --newest-post-at ISO --note "..."
        Same rules as checkpoint.py: only --status ok moves the cursor.

data/cramer.json is one row per (post, ticker). See README section 7.
"""
import argparse, datetime, json, pathlib, sys, time, urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
UA = {"User-Agent": "Mozilla/5.0"}
DATA = ROOT / "data/cramer.json"
STOCKS = ROOT / "data/cramer_stocks.json"
CP = ROOT / "data/cramer_checkpoint.json"
SHOTS = ROOT / "cramer"
WINDOW_DAYS = 15          # never scan further back than this before his newest post
STANCES = {"Bullish", "Bearish", "Neutral"}
KINDS = {"Stock", "ETF", "Crypto"}
REQUIRED = ["id", "post_id", "post", "posted_at", "date", "time", "ticker", "company", "kind", "stance", "said", "shot"]


# ---------- Yahoo ----------
def chart(ticker, rng, interval):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={rng}&interval={interval}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as fh:
                return json.load(fh)["chart"]["result"][0]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            raise

def bars(d):
    """[(datetime NY, open, close)] with None closes kept (caller decides)."""
    q = d["indicators"]["quote"][0]
    return [(datetime.datetime.fromtimestamp(t, NY), o, c)
            for t, o, c in zip(d.get("timestamp") or [], q.get("open") or [], q.get("close") or [])]

def session_open(day):
    return datetime.datetime.combine(day, datetime.time(9, 30), NY)

def session_close(day):
    return datetime.datetime.combine(day, datetime.time(16, 0), NY)


def price_at(ticker, posted_utc, intraday, daily, company):
    """Price when he posted.

    - During the regular session: the close of the last finished 5-minute bar
      before the post (the open of the first bar if he posted in the first five minutes).
    - Outside the session: the last regular-session close before the post.
    - Before the stock's first trade (e.g. Anthropic before its Nov 19 IPO):
      the first trade, i.e. the open of its first day.
    Returns (price, at_iso, label).
    """
    t = posted_utc.astimezone(NY)
    day_bars = [b for b in intraday if b[0].date() == t.date() and b[2] is not None]
    if day_bars and session_open(t.date()) <= t < session_close(t.date()) and day_bars[0][0] <= t:
        done = [b for b in day_bars if b[0] + datetime.timedelta(minutes=5) <= t]
        if done:
            b = done[-1]
            end = b[0] + datetime.timedelta(minutes=5)
            return round(b[2], 2), end.isoformat(), f"{end:%-I:%M %p} ET, the last 5-minute bar before the post"
        b = day_bars[0]
        return round(b[1], 2), b[0].isoformat(), f"{b[0]:%-I:%M %p} ET, that day's first trade"
    closes = [b for b in daily if b[2] is not None and session_close(b[0].date()) <= t]
    if closes:
        b = closes[-1]
        d = b[0].date()
        if d == t.date():
            why = "posted after the close"
        elif t.weekday() >= 5:
            why = "posted on the weekend"
        else:
            why = "posted before the open"
        return round(b[2], 2), session_close(d).isoformat(), f"{d:%b %-d} close ({why})"
    first = [b for b in daily if b[1] is not None]
    if first:
        b = first[0]
        return round(b[1], 2), b[0].isoformat(), f"First trade, {b[0]:%b %-d} open (posted before {company} listed)"
    return None, None, None


def cmd_prices(a):
    rows = json.load(open(DATA))
    now = datetime.datetime.now(NY)
    tickers = []
    for r in rows:
        if r["ticker"] not in tickers:
            tickers.append(r["ticker"])
    old = {s["ticker"]: s for s in (json.load(open(STOCKS)) if STOCKS.exists() else [])}
    stocks, filled, failed = [], 0, []
    for tk in tickers:
        try:
            dd = chart(tk, "3mo", "1d")
            time.sleep(0.3)
            need = [r for r in rows if r["ticker"] == tk and r.get("price_then") is None]
            intra = []
            if need:
                intra = bars(chart(tk, "1mo", "5m"))
                time.sleep(0.3)
        except Exception as e:
            failed.append(f"{tk} ({type(e).__name__})")
            if tk in old:
                stocks.append(old[tk])
            continue
        daily = bars(dd)
        for r in need:
            posted = datetime.datetime.strptime(r["posted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC)
            p, at, label = price_at(tk, posted, intra, daily, r["company"])
            if p is not None:
                r["price_then"], r["price_then_at"], r["price_then_label"] = p, at, label
                filled += 1
        m = dd["meta"]
        # completed sessions only: drop today's bar while the market is open
        closes = [(b[0].date().isoformat(), round(b[2], 2)) for b in daily
                  if b[2] is not None and not (b[0].date() == now.date() and now < session_close(now.date()))]
        stocks.append({
            "ticker": tk,
            "name": m.get("longName") or m.get("shortName") or tk,
            "exchange": m.get("fullExchangeName") or m.get("exchangeName"),
            "currency": m.get("currency"),
            "high52": m.get("fiftyTwoWeekHigh"),
            "low52": m.get("fiftyTwoWeekLow"),
            "closes": closes,
        })
    json.dump(rows, open(DATA, "w"), indent=1, ensure_ascii=False)
    json.dump(stocks, open(STOCKS, "w"), indent=1, ensure_ascii=False)
    left = sum(1 for r in rows if r.get("price_then") is None)
    print(f"cramer prices: filled {filled}, still missing {left}; cramer_stocks.json {len(stocks)} tickers"
          + (f"; failed: {', '.join(failed)}" if failed else ""))
    if failed and len(failed) > len(tickers) / 4:
        sys.exit(1)


# ---------- screenshots ----------
def cmd_shot(a):
    from PIL import Image
    parts = [Image.open(p).convert("RGB") for p in a.png]
    if len(parts) > 1:
        w = max(p.width for p in parts)
        out = Image.new("RGB", (w, sum(p.height for p in parts)), parts[0].getpixel((1, 1)))
        y = 0
        for p in parts:
            out.paste(p, (0, y)); y += p.height
    else:
        out = parts[0]
    SHOTS.mkdir(exist_ok=True)
    dest = SHOTS / f"{a.post_id}.webp"
    out.save(dest, format="WEBP", quality=80, method=6)
    print(f"{dest.relative_to(ROOT)}  {out.width}x{out.height}  {dest.stat().st_size // 1024} KB")


# ---------- checks ----------
def cmd_check(a):
    rows = json.load(open(DATA))
    comp = {c["ticker"] for c in json.load(open(ROOT / "data/companies.json"))}
    problems = []
    ids = set()
    for r in rows:
        for f in REQUIRED:
            if r.get(f) in (None, ""):
                problems.append(f"{r.get('id')}: missing {f}")
        if r.get("id") in ids:
            problems.append(f"{r['id']}: duplicate id")
        ids.add(r.get("id"))
        if r.get("stance") not in STANCES:
            problems.append(f"{r['id']}: stance {r.get('stance')!r}")
        if r.get("kind") not in KINDS:
            problems.append(f"{r['id']}: kind {r.get('kind')!r}")
        if r.get("shot") and not (ROOT / r["shot"]).exists():
            problems.append(f"{r['id']}: screenshot {r['shot']} not on disk")
        if r.get("ticker") not in comp:
            problems.append(f"{r['id']}: no companies.json row for {r.get('ticker')}")
        if r.get("price_then") is None:
            problems.append(f"{r['id']}: no price_then yet ({r.get('ticker')})")
    dup = {}
    for r in rows:
        dup.setdefault((r["post_id"], r["ticker"]), []).append(r["id"])
    problems += [f"{v}: same post and ticker twice" for v in dup.values() if len(v) > 1]
    posts = len({r["post_id"] for r in rows})
    print(f"cramer.json: {len(rows)} rows from {posts} posts, {len({r['ticker'] for r in rows})} tickers")
    for p in problems:
        print("  -", p)
    if problems:
        sys.exit(1)


# ---------- checkpoint ----------
def load_cp():
    if CP.exists():
        return json.load(open(CP))
    return {"confirmed_through": None, "newest_post_id": None, "newest_post_at": None,
            "last_run_at": None, "last_run_status": None, "history": []}

def cmd_show(a):
    c = load_cp()
    rows = json.load(open(DATA)) if DATA.exists() else []
    if not CP.exists():
        print("No Cramer checkpoint yet: scan the 15 days before his newest post.")
    else:
        print(f"confirmed through : {c.get('confirmed_through') or '(none)'}")
        print(f"newest post read  : {c.get('newest_post_id') or '(none)'}")
        print(f"last run          : {c.get('last_run_at')}  status={c.get('last_run_status')}")
    newest = max((r["date"] for r in rows), default=None)
    print(f"data              : {len(rows)} rows from {len({r['post_id'] for r in rows})} posts, newest post dated {newest}")
    print(f"rule              : scan back past confirmed_through, but never more than {WINDOW_DAYS} days before his newest post")
    bad = []
    for h in c.get("history", []):
        if h.get("status") == "ok":
            break
        bad.append(h)
    if bad:
        print(f"\n{len(bad)} earlier run(s) did not finish the Cramer scan; the gap since {c.get('confirmed_through')} is still open:")
        for h in bad[:5]:
            print(f"  {h['at']}  {h['status']}  {h.get('note', '')}")

def cmd_record(a):
    c = load_cp()
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.status == "ok":
        if a.newest_post_id:
            c["newest_post_id"] = a.newest_post_id
        if a.newest_post_at:
            c["confirmed_through"] = a.newest_post_at
            c["newest_post_at"] = a.newest_post_at
    c["last_run_at"], c["last_run_status"] = now, a.status
    rows = json.load(open(DATA)) if DATA.exists() else []
    c["data"] = {"rows": len(rows), "posts": len({r["post_id"] for r in rows}),
                 "newest_row_id": rows[-1]["id"] if rows else None}
    c.setdefault("history", []).insert(0, {"at": now, "status": a.status, "note": a.note or ""})
    c["history"] = c["history"][:20]
    json.dump(c, open(CP, "w"), indent=1)
    moved = "cursor advanced" if a.status == "ok" and a.newest_post_at else "cursor unchanged"
    print(f"cramer checkpoint: {a.status}, {moved}, confirmed through {c.get('confirmed_through')}")


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("show"); s.add_parser("prices"); s.add_parser("check")
    sh = s.add_parser("shot"); sh.add_argument("post_id"); sh.add_argument("png", nargs="+")
    r = s.add_parser("record")
    r.add_argument("--status", required=True, choices=["ok", "posts-unread", "partial"])
    r.add_argument("--newest-post-id"); r.add_argument("--newest-post-at"); r.add_argument("--note")
    a = p.parse_args()
    {"show": cmd_show, "prices": cmd_prices, "check": cmd_check, "shot": cmd_shot, "record": cmd_record}[a.cmd](a)

if __name__ == "__main__":
    main()
