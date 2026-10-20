#!/usr/bin/env python3
"""Rebuild the dashboard from data/*.json.

- stamps data/meta.json with today's date (the "Last updated" bubble)
- rewrites the inline window.__DATA block in dashboard/standalone.html
- copies standalone.html to index.html, which is what GitHub Pages serves

Run this after any change to data/*.json. publish.sh calls it for you.
"""
import json, re, shutil, sys, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
KEYS = ["trades", "portfolios", "companies", "quotes", "meta"]

def main():
    stamp = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    json.dump([{"updated": stamp}], open(ROOT / "data/meta.json", "w"), indent=1)

    parts = []
    for k in KEYS:
        rows = json.load(open(ROOT / f"data/{k}.json"))
        parts.append(f"{k}: [\n" + ",\n".join(" " + json.dumps(r, ensure_ascii=False) for r in rows) + "\n]")
    block = "window.__DATA = { " + ", ".join(parts) + " };"

    page = ROOT / "dashboard/standalone.html"
    s = page.read_text()
    s, n = re.subn(r"window\.__DATA = \{ .*?\n\] \};", lambda m: block, s, flags=re.S)
    if n != 1:
        sys.exit(f"__DATA block matched {n} times — aborting")
    page.write_text(s)
    shutil.copy(page, ROOT / "index.html")

    counts = ", ".join(f"{k} {len(json.load(open(ROOT / f'data/{k}.json')))}" for k in KEYS)
    print(f"synced ({counts}); last updated {stamp}")

if __name__ == "__main__":
    main()
