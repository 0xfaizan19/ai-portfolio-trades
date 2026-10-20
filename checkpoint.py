#!/usr/bin/env python3
"""Checkpoint for the daily routine: where the last update got to.

`sources.md` is the human-readable record of posts read. This file is the
machine-readable resume point, so a run that is skipped, interrupted or
unable to reach X does not lose its place.

    python3 checkpoint.py show
    python3 checkpoint.py record --status ok \
        --newest-post-id 2112312565468471417 \
        --newest-post-at 2026-10-19T22:38:55Z \
        --note "no new trades"

The cursor only moves on `--status ok`. Any other status records the attempt
and leaves `confirmed_through` where it was, so the next run rescans the gap
instead of stepping over it.
"""
import json, sys, argparse, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent
CP = ROOT / "data/checkpoint.json"
STATUSES = ["ok", "posts-unread", "partial"]

def counts():
    out = {}
    for k in ("trades", "portfolios", "companies", "quotes"):
        try:
            out[k] = len(json.load(open(ROOT / f"data/{k}.json")))
        except Exception:
            out[k] = None
    try:
        tr = json.load(open(ROOT / "data/trades.json"))
        out["newest_trade_id"] = max((t["id"] for t in tr), default=None)
        out["newest_trade_date"] = max((t["date"] for t in tr), default=None)
    except Exception:
        pass
    try:
        out["quotes_as_of"] = max(q["as_of"] for q in json.load(open(ROOT / "data/quotes.json")))
    except Exception:
        pass
    return out

def load():
    if CP.exists():
        return json.load(open(CP))
    return {"confirmed_through": None, "newest_post_id": None, "newest_post_at": None,
            "last_run_at": None, "last_run_status": None, "data": {}, "history": []}

def show():
    c = load()
    if not CP.exists():
        print("No checkpoint yet — treat every post as unread and scan back as far as sources.md goes.")
        return
    print(f"confirmed through : {c.get('confirmed_through') or '(none)'}")
    print(f"newest post read  : {c.get('newest_post_id') or '(none)'}")
    print(f"last run          : {c.get('last_run_at')}  status={c.get('last_run_status')}")
    d = c.get("data", {})
    print(f"data              : trades {d.get('trades')} (newest {d.get('newest_trade_id')}, "
          f"{d.get('newest_trade_date')}), quotes as of {d.get('quotes_as_of')}")
    bad = [h for h in c.get("history", []) if h.get("status") != "ok"]
    if bad:
        print(f"\n{len(bad)} earlier run(s) did not complete the post scan — the gap since "
              f"{c.get('confirmed_through')} has not been covered yet:")
        for h in bad[:5]:
            print(f"  {h['at']}  {h['status']}  {h.get('note','')}")

def record(a):
    c = load()
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.status == "ok":
        if a.newest_post_id:
            c["newest_post_id"] = a.newest_post_id
        if a.newest_post_at:
            c["confirmed_through"] = a.newest_post_at
            c["newest_post_at"] = a.newest_post_at
    c["last_run_at"] = now
    c["last_run_status"] = a.status
    c["data"] = counts()
    c.setdefault("history", []).insert(0, {"at": now, "status": a.status, "note": a.note or ""})
    c["history"] = c["history"][:20]
    json.dump(c, open(CP, "w"), indent=1)
    moved = "cursor advanced" if a.status == "ok" and a.newest_post_at else "cursor unchanged"
    print(f"checkpoint: {a.status}, {moved}, confirmed through {c.get('confirmed_through')}")

def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("show")
    r = s.add_parser("record")
    r.add_argument("--status", required=True, choices=STATUSES)
    r.add_argument("--newest-post-id")
    r.add_argument("--newest-post-at")
    r.add_argument("--note")
    a = p.parse_args()
    show() if a.cmd == "show" else record(a)

if __name__ == "__main__":
    main()
