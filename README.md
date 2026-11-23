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

Since Nov 23, 2026 the same page also has a **Jim Cramer on X** section: every stock or crypto that Jim Cramer (@jimcramer) names in a post, whether he sounded bullish, bearish or neutral, a screenshot of the post, a link to it, the price when he posted, and how the stock has moved since. It started with the 15 days before his newest post (Nov 8 to Nov 23, 2026) and is updated by the same daily routine. See sections 3, 4 and 7.

## 2. Files

```
ai-portfolio-trades/
├── README.md                  ← this file
├── index.html                 ← what GitHub Pages serves; a copy of dashboard/standalone.html, rebuilt by sync.py
├── checkpoint.py              ← show / record the daily routine's resume point
├── cramer.py                  ← Jim Cramer section: screenshots, prices at post time, its own checkpoint (section 7)
├── cramer/                    ← one screenshot per Cramer post, <post id>.webp (served next to index.html)
├── refresh_quotes.py          ← rewrites data/quotes.json with the latest close for every ticker (trades + Cramer)
├── sync.py                    ← stamps meta.json, rebuilds the inline data, regenerates index.html
├── publish.sh                 ← runs sync.py, commits and pushes in one command
├── Open Dashboard.command     ← double-click to open the local copy in Chrome
├── data/
│   ├── trades.json            ← one row per buy or sell (the main dataset)
│   ├── portfolios.json        ← one row per portfolio: return figure + notes
│   ├── companies.json         ← one row per ticker: what the company is and how it makes money
│   ├── quotes.json            ← latest closing price per ticker (snapshot; refresh on every update)
│   ├── meta.json              ← {"updated": "YYYY-MM-DD"} behind the "Last updated" bubble; sync.py stamps it
│   ├── checkpoint.json        ← where the daily routine got to; written by checkpoint.py, not by hand
│   ├── cramer.json            ← one row per (Cramer post, ticker): stance, summary, screenshot, price then
│   ├── cramer_stocks.json     ← per Cramer ticker: listing name, 52-week range, ~3 months of daily closes (cramer.py prices)
│   └── cramer_checkpoint.json ← where the Cramer scan got to; written by cramer.py record, not by hand
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

`[{ticker, price, as_of}]`: the latest daily close from Yahoo Finance (`.../v8/finance/chart/<T>?range=5d&interval=1d`, last close), for every ticker in trades.json **and** cramer.json. **Refresh it on every update.** Since Nov 23, 2026 `refresh_quotes.py` handles two Yahoo quirks itself: during market hours it skips today's unfinished bar (so a mid-session run keeps the last real close), and when Yahoo leaves a finished day's close empty (Sandisk, Nov 20) it uses that day's 4:00 PM price, the close already stored for that day, or the 4:00 PM bar, in that order, and prints a `note:` line saying which. It still lists any ticker whose close is older than the rest; check that line. The "How it has gone so far" box uses it:
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

### `data/cramer.json`: one object per (Jim Cramer post, ticker)

A post that names three stocks is three rows sharing `post_id`, `post` and `shot`. Ids run oldest first.

| Field | Example | Meaning |
|---|---|---|
| `id` | `"c083"` | Unique and stable. Continue the sequence. |
| `post_id` | `"2123601543710523515"` | The X status id (a snowflake, so it sorts by time) |
| `post` | `"https://x.com/jimcramer/status/…"` | Link to the post. Shown in the table and the popup. |
| `posted_at` | `"2026-11-20T02:17:00Z"` | Exact UTC time, from the snowflake: `((id >> 22) + 1288834974657) / 1000` |
| `date`, `time` | `"2026-11-19"`, `"9:17 PM"` | The same moment in New York time |
| `ticker`, `company` | `"AMD"`, `"AMD"` | Yahoo symbol and short name. Crypto uses Yahoo's pair, e.g. `BTC-USD`. Needs a companies.json row. |
| `kind` | `"Stock"` | `Stock`, `ETF` or `Crypto` |
| `stance` | `"Bullish"` | `Bullish`, `Bearish` or `Neutral` (rules in section 7) |
| `said` | | One or two plain sentences, paraphrased; the screenshot is the verbatim record |
| `shot` | `"cramer/2123601543710523515.webp"` | Screenshot path, relative to index.html |
| `price_then` | `489.19` | Price when he posted (filled by `cramer.py prices`, see section 7) |
| `price_then_at`, `price_then_label` | | When that price is from, and the same in words, e.g. `"Nov 19 close (posted after the close)"` |

### `data/cramer_stocks.json`: one object per Cramer ticker

`{ticker, name, exchange, currency, high52, low52, closes: [[YYYY-MM-DD, close], …]}` from Yahoo's chart endpoint (about three months of finished sessions). `cramer.py prices` rebuilds it; the popup's chart, 52-week range and listing line read it.

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

5. **Jim Cramer on X** (`#cramer`, below the trade log; the title has jump links to both sections). Stat tiles (posts tracked, bullish / bearish / neutral counts with the average move since, how many bullish-or-bearish calls are going his way, the most-mentioned ticker), stance chips (All / Bullish / Bearish / Neutral) and a search box, then a table: Posted, Ticker, Company, His take, What he said, Price then, Since, and a **View on X ↗** link. "Since" is latest close ÷ `price_then` − 1, and shows "—" until a close exists after the post (`quotes.as_of` earlier than the post's date). Company, Price then and the link column hide on narrow screens.

   **Clicking a row opens a popup** (a `<dialog>`; Esc, × or a click outside closes it, and focus returns to the row). It shows the stance, ticker and company; the posting time with an **Open the post on X ↗** link; the screenshot, which also links to the post; what he said; four facts (price when he posted, latest close, move since, and whether the call is going his way); "Also in this post" chips for other tickers in the same post; a 3-month daily-close chart with a "He posted" marker, a hover/arrow-key read-out and a table view; the listing name and 52-week range; every other post of his on that ticker; any AI-portfolio trades in it (a button opens that trade's page); and the company profile from companies.json. The URL becomes `#cramer-<id>`, so a popup can be shared or bookmarked.

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

### The checkpoint

`sources.md` is the human-readable record of posts read. `data/checkpoint.json` is the machine-readable resume point, so a run that is skipped, interrupted or unable to reach X does not lose its place.

```bash
python3 checkpoint.py show      # where the last update got to — run this FIRST, before reading X
```

Scan back past `confirmed_through`, not merely past the last post you happen to recognise. At the end of every run, record what happened:

```bash
# X was read all the way back to the checkpoint
python3 checkpoint.py record --status ok \
    --newest-post-id <id> --newest-post-at <ISO8601> --note "<what changed>"

# X could not be read at all (Chrome shut, logged out, app closed at 7am)
python3 checkpoint.py record --status posts-unread --note "<why>"

# posts were read but something else failed part-way
python3 checkpoint.py record --status partial --note "<what is incomplete>"
```

**The cursor only moves on `--status ok`.** Anything else logs the attempt and leaves `confirmed_through` where it was, so the gap widens and the next successful run covers all of it. `checkpoint.py show` then prints a warning naming that uncovered gap, so missed days get picked up instead of stepped over. Always record a status, including when the run failed — a run that records nothing looks exactly like a run that never happened.

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

## 7. Jim Cramer on X (part of the daily routine)

### What gets recorded

- **Account:** https://x.com/jimcramer ("Host of @madmoneyoncnbc"). Read it logged in, in the routine's Chrome, exactly like @aifinancelabs.
- **Window:** everything after `confirmed_through` in `data/cramer_checkpoint.json`, but **never more than 15 days before his newest post** (the owner's rule, Nov 23, 2026). If runs were missed for longer than that, skip what is older and say so in the note.
- **Which posts:** his own posts and quote posts (the Posts tab). Not replies, not his reposts of other people, not a pinned post.
- **Which rows:** one row per stock, ETF or crypto he names or clearly refers to, by name, ticker, cashtag, or a photo that shows it (Nov 18: TJX on the NYSE board). Market-wide calls (the S&P 500, "time to start buying" on his oscillator), commodities (oil, copper), private companies, and sports or personal posts get no row. Tickers that only appear inside someone else's quoted post (the $GS $APO $BX cashtags in a WSJ quote) get no row unless he talks about them.
- **Stance**, judged from his words in that post:
  - **Bullish:** he says to buy, own or like it, defends the stock or its management, calls a drop overdone, or calls the news good for it.
  - **Bearish:** he says to sell, avoid or short it, expects it to fall, or calls a development bad for it ("very disappointing", "just plain awful").
  - **Neutral:** news, color, a joke, a question, a promo for his own piece or video, or a mixed take. Neutral rows are kept; they show what he talked about.
- **`said`:** one or two plain sentences, paraphrased. No long quotes; the screenshot is the verbatim record.

### Step A: read the posts

```bash
python3 cramer.py show
```

Open https://x.com/jimcramer and harvest `article` elements by date, the same way as for @aifinancelabs (section 5), back past `confirmed_through` and at most 15 days before his newest post. Cross-check with X search `from:jimcramer since:<YYYY-MM-DD> -filter:replies` (Latest tab); on Nov 23 the two matched exactly.

The Chrome `javascript_tool` truncates results over roughly 1,000 characters and blocks text with `?`, `&`, `=` or `%` in it, so strip those characters. To read many posts at once, build the lines in `window`, replace `document.body.innerHTML` with one `<article><pre>` holding them, call `get_page_text`, then navigate away.

### Step B: screenshot every post that gets a row

For each post, navigate to `https://x.com/jimcramer/status/<id>`, wait about 3 s, and run this in the page. It finds the post, zooms it to 1.5× so the image is sharp (less if the post would not fit the window), and returns the crop box:

```js
(() => { const id = location.pathname.split('/').pop(); const arts = [...document.querySelectorAll('article')];
  const art = arts.find(a => [...a.querySelectorAll('a[href*="/status/"]')].some(l => l.getAttribute('href').endsWith('/status/' + id)) && a.querySelector('time')) || arts[0];
  art.scrollIntoView({block: 'start'}); window.scrollBy(0, -60);
  const r0 = art.getBoundingClientRect(), bar0 = art.querySelector('[role="group"]');
  const h0 = (bar0 ? bar0.getBoundingClientRect().bottom : r0.bottom) - r0.top;
  const z = Math.max(0.5, Math.floor(Math.min(1.5, (innerHeight - 66) / h0) * 100) / 100);
  Object.assign(art.style, {width: r0.width + 'px', zoom: String(z), position: 'relative', zIndex: '9999', background: getComputedStyle(document.body).backgroundColor});
  art.scrollIntoView({block: 'start'}); window.scrollBy(0, -60);
  const r = art.getBoundingClientRect(), b = (art.querySelector('[role="group"]') || art).getBoundingClientRect();
  return [id, Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(b.bottom) + 2, z]; })()
```

Move the mouse off the post (`hover` near the window's bottom-right corner), then use the `computer` tool's `zoom` action with `region: [left, top, right, bottom]` and `save_to_disk: true` at the default scale (a smaller `scale` also shrinks the saved file). The crop ends at the reply/repost/like bar, so it never shows the signed-in account. Then:

```bash
python3 cramer.py shot <post id> <saved .png>        # writes cramer/<post id>.webp, about 25-40 KB
```

- **Tall posts** (the zoom would drop below about 0.9, e.g. a quote of a WSJ chart): set the zoom to 1.2, capture the visible part, `scrollBy(0, 560)`, re-measure, capture from the line where the first part ended to the bottom, and pass both files; `cramer.py shot <id> part1.png part2.png` stacks them.
- **Cashtags** such as `$CRWV` can render X's live price card ("Trade on …"). It shows today's price, not the price when he posted, so hide it before capturing: `display:none` on the smallest element containing both "Trade on" and the company name but not the post text.
- If X shows only its logo after many page loads in a row, wait about 10 s and load the post again.
- One post per round trip works well: `[zoom the previous post, navigate to the next, wait, run the script, hover]`.

### Step C: add the rows and fill the prices

Append the rows to `data/cramer.json` (fields in section 3, `price_then*` left null) and add a companies.json row for every new ticker. Resolve names with Yahoo's `https://query1.finance.yahoo.com/v1/finance/search?q=<name>`; in this timeline Anthropic is ANT, SpaceX SPCX, Cerebras CBRS, Qnity Q, and SK hynix's US listing SKHY. Then:

```bash
python3 cramer.py prices     # fills price_then for new rows and rebuilds data/cramer_stocks.json
python3 cramer.py check      # every row has its fields, a valid stance, its screenshot, a company row and a price
```

How `price_then` is chosen: during the regular session (9:30 AM to 4:00 PM ET), the close of the last finished 5-minute bar before the post; outside it, the last regular-session close before the post; before the stock's first trade (Anthropic before its Nov 19 IPO), the first trade, which is its first day's open. Yahoo keeps 5-minute bars for only about a month, so fill prices on the run that adds the rows.

### Step D: record the Cramer checkpoint

```bash
python3 cramer.py record --status ok --newest-post-id <id> --newest-post-at <ISO 8601> --note "<what was added, or no new posts>"
python3 cramer.py record --status posts-unread --note "<why X could not be read>"
python3 cramer.py record --status partial --note "<what is incomplete>"
```

The same rules as `checkpoint.py`: only `ok` moves the cursor. `./publish.sh` then commits the new rows and screenshots with everything else.

### Notes

- The first run (Nov 23, 2026) recorded 79 posts and 89 rows, from Nov 8, 12:15 PM ET to Nov 23, 12:15 PM ET: 45 bullish, 5 bearish, 39 neutral, across 24 tickers. Nvidia's CEO turmoil dominated (48 rows).
- He posts about 7 times a day, roughly 5 of them about a stock. Screenshots average about 27 KB, so the folder grows by about 0.15 MB a day.
- The Claude Dashboard artifact (`dashboard-page.html`) has no `cramer` dataset, so the section there says "No Cramer data in this view."
