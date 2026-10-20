# AI Portfolio Trades: handoff pack

This pack has everything needed to rebuild and maintain a dashboard of the buys and sells made by the AI-run portfolios that **@aifinancelabs** posts about on X (https://x.com/aifinancelabs).

If you are an AI picking this up, read this whole file first. Then open `dashboard/standalone.html` to see the finished result.

---

## 1. What this is

@aifinancelabs runs public portfolios on Autopilot (joinautopilot.com), each managed by an LLM:

| Portfolio | Model | Notes |
|---|---|---|
| Claude | Anthropic Claude | About $50M under management. The main book. |
| Claude WW3 | Anthropic Claude | "AI World War III Portfolio", defense-focused, $89.3M tracking it |
| GPT | OpenAI ChatGPT | |
| Grok | xAI Grok | |
| DeepSeek | DeepSeek | Pinned post claims about 82% over 12 months |

The owner wants to track **what each AI bought or sold, how much (as a share of the portfolio), at what price, and when**. The goal is one dashboard they can check.

The current version covers the **last 10 posts as of Oct 19, 2026**, with trades dated Sep 30 to Oct 8, 2026.

## 2. Files

```
ai-portfolio-trades/
├── README.md                  ← this file
├── index.html                 ← what GitHub Pages serves; a copy of dashboard/standalone.html, rebuilt by sync.py
├── refresh_quotes.py          ← rewrites data/quotes.json with the latest close for every ticker
├── sync.py                    ← stamps meta.json, rebuilds the inline data, regenerates index.html
├── publish.sh                 ← runs sync.py, commits and pushes in one command
├── Open Dashboard.command     ← double-click to open the local copy in Chrome
├── data/
│   ├── trades.json            ← one row per buy or sell (the main dataset)
│   ├── portfolios.json        ← one row per portfolio: return figure + notes
│   ├── companies.json         ← one row per ticker: what the company is and how it makes money
│   ├── quotes.json            ← latest closing price per ticker (snapshot; refresh on every update)
│   └── meta.json              ← {"updated": "YYYY-MM-DD"} behind the "Last updated" bubble; sync.py stamps it
├── dashboard/
│   ├── standalone.html        ← opens in any browser; data built in (needs internet for d3)
│   └── dashboard-page.html    ← the page as written for Claude's "Dashboard" artifact type
└── sources.md                 ← every post used, with links and what it said
```

## 3. Data format

### `data/trades.json`: array of objects, one per trade leg

| Field | Type | Example | Meaning |
|---|---|---|---|
| `id` | string | `"t01"` | Unique and stable. Continue the sequence (`t16`, `t17`, …). |
| `date` | `YYYY-MM-DD` | `"2026-10-08"` | Day the trade was **executed**, not the day it was posted (see rules below) |
| `model` | string | `"Claude"` | The LLM: Claude, GPT, Grok or DeepSeek |
| `portfolio` | string | `"Claude WW3"` | Which book. Must match a `portfolio` in portfolios.json. |
| `action` | `"Buy"` or `"Sell"` | `"Sell"` | Exactly these two values |
| `ticker` | string | `"VST"` | Stock symbol |
| `company` | string | `"Vistra"` | Company name |
| `size` | string | `"Trim 13% → 4%"` | Size in the post's own words, or `"Not disclosed"` |
| `size_pct` | number or null | `9` | Percentage points of the portfolio that changed, if known |
| `price` | number or null | `165.81` | Price per share in USD (see `price_source`) |
| `price_source` | string | `"From the post"` | One of: `"From the post"` (the post states the fill), `"Day's open"` (the post says "at the open", so the price is that day's opening price), `"Day's open (estimate)"` (the post gives only the date, so the opening price is a stand-in) |
| `price_note` | string or null | | Plain-words explanation of where the price came from, including that day's close for estimates |
| `reason` | string | `"Too concentrated…"` | One-line summary of the AI's stated reason |
| `post` | URL | `"https://x.com/aifinancelabs/status/…"` | The post it came from |
| `posted` | `YYYY-MM-DD` | `"2026-10-09"` | Day the post went up (can be after `date`) |
| `pair` | string or null | `"t02"` | `id` of the other side of a swap: where the money went, or where it came from |
| `summary` | string | | 1–2 sentences: what happened |
| `thesis` | string or null | | The AI's reasoning, paraphrased from the post (several sentences) |
| `risk` | string or null | | What the AI said could prove it wrong |
| `watch` | string or null | | Next catalyst or date to watch |
| `outcome` | string or null | | How the trade has gone so far, per later posts |

| `entry_price` | number or null | `149.00` | **Sells only:** the buy price, when a post made it public |
| `entry_when` | string or null | `"Aug 12, 2026"` | When that buy happened, as precisely as the post says (e.g. `"April 2026"`) |
| `gain_basis` | string or null | | **Sells only:** where the buy price came from, or why the gain is "Not public" |

Gain/loss is **calculated, not stored** (see the trade log notes in section 4). For sells it's `price / entry_price − 1`, or "Not public" when `entry_price` is null.

### `data/quotes.json`: latest price per ticker

`[{ticker, price, as_of}]`: the latest daily close from Yahoo Finance (`.../v8/finance/chart/<T>?range=5d&interval=1d`, last close). **Refresh it on every update.** The "How it has gone so far" box uses it:
- Buy: P&L = current ÷ buy price − 1
- Sell: P&L = (sale price − current) ÷ sale price, so it's positive (green) when the stock fell after the sale

### `data/companies.json`: one object per ticker

| Field | Meaning |
|---|---|
| `ticker`, `company` | Must match the ticker in trades.json |
| `sector`, `hq` | Short labels |
| `about` | "What it is": 1–2 plain sentences |
| `revenue` | "How it makes money": 2–3 plain sentences |
| `segments` | Main businesses, separated by ` · ` (shown as chips) |

This is general background written from public knowledge, not from the posts. Add a row whenever a new ticker appears.

Use `null`, not an empty string, when a post doesn't cover a field. The detail page shows a "not mentioned" line in its place.

A swap such as "sold RTX for Boeing" becomes **two rows**: one Sell and one Buy.

### `data/portfolios.json`: array of objects, one per portfolio

| Field | Type | Meaning |
|---|---|---|
| `portfolio` | string | Name. The order shown is Claude, Claude WW3, GPT, Grok, DeepSeek. |
| `model` | string | The LLM |
| `stat` | number or null | Headline return as a decimal (`2.0625` = +206.25%). `null` if no post gave one. |
| `stat_label` | string | What the stat means, e.g. `"Return since Oct 2023 (S&P 500: +86.0%)"` |
| `as_of` | `YYYY-MM-DD` | Date of the post that gave the stat |
| `note` | string | Notable holdings or context, such as positions mentioned without a trade |

## 4. The dashboard

From top to bottom:

1. **Title and a "Last updated" bubble** in the top right, fed by `data/meta.json`. `sync.py` stamps it with the current date on every run, so it tracks the trade log automatically. There is no takeaway sentence; it was removed.
2. **Portfolio cards**, all on one row (`--aft-cols` is set from the number of portfolios; below 900px they scroll sideways instead of wrapping). Each shows the colored name, the headline return (or "—"), the period and the date it was measured, buy and sell counts, and then **the S&P 500 over the same period and the gap in percentage points**, green when ahead and red when behind. The `note` field is still in the data but is no longer displayed.

   `stat` and `benchmark` must come from the **same post**, so both numbers cover the same window — that is why portfolios carry different `as_of` dates. If a newer post gives a return without an S&P figure, keep the older matched pair rather than mixing them.
3. **Trade log table.** Columns include Price, Price from and **Gain / loss vs. the buy price**:
   - **Open position** (a buy not yet sold): latest close from quotes.json ÷ buy price − 1, as plain green or red text. It updates whenever quotes.json is refreshed.
   - **Final** (a sell with a public buy price, or a buy later sold in the same portfolio): sale price ÷ buy price − 1, shown inside a **bubble** (a pill with a colored outline) so it reads as locked in.
   - "Not public" for a sell whose buy price was never posted.
   The `gains` calc in the page script does this math. Newest first. **Clicking a row (or pressing Enter on it) opens that trade's detail page**. There is no subtitle or legend under the heading; both were removed. A search box matches ticker, company or reason.

   **Portfolio chips are multi-select.** `window.aftFilter.sel` is a `Set`: clicking a portfolio toggles it, so several can be on at once, and an empty set means everything. Clicking **All** clears the set, which deselects every portfolio and shows the full log. Columns: Date, Portfolio, Action (green Buy / red Sell pill), Ticker, Company, Size, Price, Why. Company and Why hide on narrow screens.

4. **Trade detail page** (one per trade). It is a centered column (max 60rem wide). It replaces the list view, and "← All trades" goes back. It shows:
   - a large blue "← All trades" button (`.aft-back`), then a Buy/Sell pill, ticker and company, then the `summary`
   - fact tiles: Portfolio, Model, Traded (`date`), Posted, Size, then the price. A buy shows "Bought at". A sell shows **"Bought at"** (`entry_price` + `entry_when`, or "Not public") **and** "Sold at", plus a Gain / loss tile.
   - cards: "Why <model> made this trade" (`thesis`), "What could go wrong" (`risk`), "What to watch next" (`watch`), and "How it has gone so far". That last card shows **only** the current price (with its date) and the % P&L in green or red, computed from quotes.json, set in the sans-serif face at 1.6rem/600 for legibility (`.aft-nowv`). The owner asked for exactly that, so no text goes in it. The `outcome` field is kept in the data but not displayed.
   - "Where the money went / came from", a button that opens the `pair` trade
   - **About the company**: sector, HQ, "What it is", "How it makes money" and main-business chips (from companies.json), placed right under "How it has gone so far"
   - for sells, a **Gain / loss** tile (green or red) showing the buy price it's measured against, plus a line explaining the basis
   - a link to the original post on X
   The URL ends in `#trade-<id>` (e.g. `#trade-t07`), so a trade's page can be shared or bookmarked.

The owner asked for the "Buys and sells by portfolio" bar chart to be **removed**. Don't add it back.

### Two versions of the page

- **`standalone.html`** works anywhere. The data sits inline in `window.__DATA`. A small shim gives it the same `dash.data` / `dash.calc` / `dash.onData` API as the original. To update it, replace the two arrays in `window.__DATA` with the new contents of the JSON files.
- **`dashboard-page.html`** is the body used inside Claude's Dashboard artifact (https://claude.ai/artifact/DnrnMjkH2GqbDfFAm9tLCo, private to the owner). It expects that environment's `dash` API, `d3` global and CSS tokens (`--color-*`, `--cds-*`). The live artifact reads the two JSON files as attached datasets named `trades` and `portfolios`.

You can also rebuild the page in any stack (React, Notion, Sheets, etc.) from the JSON alone.

## 4b. Where it lives

- **Live dashboard: https://0xfaizan19.github.io/ai-portfolio-trades/** — this link never changes. It is served by GitHub Pages from `main`, repo root.
- Repo: https://github.com/0xfaizan19/ai-portfolio-trades (public — GitHub Pages needs a public repo on a free plan).
- `index.html` at the repo root is a **byte copy of `dashboard/standalone.html`**. Never edit it by hand; `publish.sh` regenerates it. Editing only `standalone.html` and pushing will leave the live site stale.

### Publishing a change

```bash
./publish.sh "what changed"
```

That runs `sync.py` — which stamps `data/meta.json` with today's date, rewrites the inline `window.__DATA` in `dashboard/standalone.html` from `data/*.json`, and copies the result to `index.html` — then commits everything and pushes. GitHub Pages rebuilds in roughly a minute, and the link above serves the new version. Check it went out with `gh api repos/0xfaizan19/ai-portfolio-trades/pages --jq .status` (wait for `built`).

So a full update is: edit `data/*.json` → `./publish.sh "what changed"`. Never hand-edit `index.html` or the `window.__DATA` block; `sync.py` owns both.

## 5. How to update it (the recurring job)

### Step 1: Read new posts

- Open https://x.com/aifinancelabs **while logged in**, using Claude-in-Chrome (the user's own Chrome, "Browser 1", deviceId `a0a7abb7-3c75-4446-bb48-81a4e43e0768`, signed in as @faizanmoltbot). The built-in browser is logged out, and logged out X stops the timeline after **6 posts** — not enough.
- Skip the pinned post (a DeepSeek promo from May 29, 2026) and its May 28 companion.
- Most posts come in pairs seconds apart: the main post, then a self-reply that only contains an Autopilot link. **Count only the main posts** — the main one is the *lower* of the two ids.
- Post ids are snowflakes, so sorting ids as numbers sorts them by time.
- **Don't trust the post count or the cursor alone — scan back by date.** The profile timeline silently omits posts: on Oct 19, 2026 a 13-post backlog had been missed this way. Scroll until you are past the oldest date already in `sources.md`, then reconcile against the table.

### Reading the posts reliably

- Harvest the timeline by scrolling and collecting `article` elements: the permalink gives the id, `time[datetime]` the timestamp. Scroll in batches of about 10 × 1.5s — a single long loop trips the 45-second CDP timeout.
- The timeline truncates long posts with "Show more". **Do not click it** — the click can land on an unrelated card and navigate away. Instead open the post's own page, `/aifinancelabs/status/<id>`, and read `[data-testid="tweetText"]`.
- `document.title` on a post page holds the opening ~250 characters of the post. That is the cheapest way to triage many posts at once: batch navigate + read title, and only open the full text for the ones that mention trades.
- Returning lots of post text in one Chrome `javascript_tool` result can trip an output filter ("BLOCKED: Cookie/query string data"), usually on the Autopilot links. Return ids and dates in bulk, then pull text post by post.

### Step 2: Pull out the trades

The post types seen so far:

| Post type | Example opener | Trades in it? |
|---|---|---|
| "BREAKING: X sold/bought…" | "BREAKING: Grok also sold all of its Broadcom at Thursday's open…" | Yes. Usually a full swap with size and sometimes prices. |
| Portfolio recap | "The AI World War III Portfolio is up 206%… Claude made three trades…" | Yes. Several dated trades, often without size. |
| Position spotlight | "Pharvaris, about 7% of Claude's portfolio, jumped 7.3%…" | No. Record it in `note` only. |
| Weekly scoreboard | "GPT's portfolio gained 2.8% last week…" | No. Update `stat` / `note`. |
| "X keeps coming back" | "DeepSeek keeps coming back 🐋 … up 77.70%…" | Usually no. Update `stat`. An older buy may be mentioned as context. |
| Video, explainer or clarification | "The Fed releases the minutes…" / "Quick clarification on the video…" | No |

Rules:

- **Use the execution date, not the post date.** "At Thursday's open" in a Friday post means the Thursday. Work out the weekday from the post's timestamp.
- Record **size as a share of the portfolio**, the way the posts state it. Don't convert to dollars or shares unless the post gives those.
- **Prices:** use the post's price when it gives one. Otherwise get that day's open (and close) from Yahoo Finance daily data and label it with `price_source`, e.g. `curl -A "Mozilla/5.0" "https://query1.finance.yahoo.com/v8/finance/chart/VST?period1=<unix start>&period2=<unix end>&interval=1d"`. That source matched every price the posts did state (VST $165.81, AVGO $370.62, RTO $19.98 on Oct 8, 2026).
- **Gain/loss on sells:** search X for the AI's original buy of that stock (`from:aifinancelabs <company>` on x.com/search, Latest tab). Use a stated cost first; replies sometimes give it (GPT: "bought Broadcom in April near $327"). Next best is a dated add or rebuild post, priced at that day's open from Yahoo. If neither exists, leave `entry_price` null. Never guess.
- Write `null` (not 0) for a missing size. Write `"Not disclosed"` in `size`.
- A trim is a Sell. Write its size as `"Trim A% → B%"` and set `size_pct` to A − B.
- Don't record trades older than what's already in the file twice. Check ticker + date + portfolio.
- If a new portfolio appears, add a row to portfolios.json and add its name to the `ORDER` array at the top of the page script.

### Step 3: Write the update

1. Append the new rows to `trades.json`, continuing the ids. Fill in `posted`, `pair`, `summary`, `thesis`, `risk`, `watch` and `outcome` from the post, paraphrased in plain words. When a later post reports how an earlier trade did, update that trade's `outcome`.
2. Update `stat`, `stat_label`, `as_of` and `note` in `portfolios.json` when a newer post gives a figure.
3. Add the new posts to `sources.md`.
4. Run `./publish.sh "…"`. `sync.py` pushes the JSON into `window.__DATA`, regenerates `index.html` and re-stamps the "Last updated" bubble — do not hand-edit any of those. **Render-logic changes still have to be made by hand in both `standalone.html` and `dashboard-page.html`**, which share identical markup and script. For the Claude artifact, upload the new JSON files as assets, then update the `trades` / `portfolios` dataset documents' `source.url`, `source.name` and `updated` fields.
5. Change "the last 10 posts" and the date range in the page copy if they no longer fit. The takeaway sentence also names the Broadcom sales and says "DeepSeek made no new trades". Rewrite that sentence when newer trades take over the headline.

## 6. Things to know

- The posts are the only source. The full live positions are on Autopilot (marketplace.joinautopilot.com), which needs an account.
- The posts say outright that they share reasoning and aren't advice. The dashboard is for tracking, not recommendations.
- Notion was the owner's first choice of home for this, but no Notion connection was available, so it became a dashboard instead. A Figma version was made and then dropped.
