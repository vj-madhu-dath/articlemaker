# n8n Amazon Discount Tracker [Track Amazon Prices & Discounts Automatically]

*Automate Amazon price monitoring with n8n and ScrapeHero — no code required.*

---

## Introduction

Manual Amazon data collection is a time sink. You visit product pages, note prices, check for discounts, and repeat — every single day. For sellers, affiliates, and deal hunters, this manual grind doesn't scale.

**Enter n8n + ScrapeHero.** This workflow automates the entire pipeline: scheduled triggers fire, search queries pull from Google Sheets, ScrapeHero's Amazon Search API fetches live listings, and results — filtered for genuine discounts — land in a dated Google Sheet tab. Zero manual copy-paste. Zero missed deals.

---

## What the Workflow Does

This n8n workflow starts with a **Schedule Trigger** that runs on your cadence (daily, hourly, custom). On each run:

1. **Creates a new sheet** inside a master Google Spreadsheet, named with today's date (e.g., `2026-01-15`).
2. **Reads search keywords** from a "Keywords" tab in the same spreadsheet.
3. **Loops over each keyword**, sending it to the **ScrapeHero Amazon Search API** via the dedicated ScrapeHero n8n node (not a generic HTTP Request).
4. **Splits the `search_results` array** into individual product items.
5. **Filters** to keep only listings that have **both** a `sale_price` *and* a `regular_price` — i.e., actual discounts.
6. **Maps fields** (ASIN, Name, Sale Price, Regular Price, % OFF, Product URL) and calculates the discount percentage.
7. **Appends** each deal to the dated sheet, using **ASIN as the unique identifier** to prevent duplicate rows across runs.

The result: a living, date-organized discount ledger you can filter, pivot, or feed into dashboards.

---

## Before You Automate

Before building, ensure you have:

| Account | Purpose |
|---------|---------|
| **n8n** (cloud or self-hosted) | Workflow orchestration |
| **Google Sheets** (Google Cloud OAuth2) | Keyword input + results storage |
| **ScrapeHero** (API key) | Amazon Search API access |

> **Tip:** Use a dedicated Google service account for n8n → Sheets auth. Grant `sheets` and `drive` scopes.

---

## Overview

```
Schedule Trigger
      │
      ▼
Create Sheet (dated tab)
      │
      ▼
Get Queries (from Keywords tab)
      │
      ▼
Loop Over Queries (SplitInBatches)
      │
      ▼
ScrapeHero Node (Amazon Search API)
      │
      ▼
Split Out Results (search_results)
      │
      ▼
Filter Has Both Prices (sale_price + regular_price exist)
      │
      ▼
Edit Fields (map + calc % OFF)
      │
      ▼
Append to Sheet (dated tab)
      │
      └──────────────┬──────────────┘
                     ▼
            Loop Over Queries (next batch)
```

---

## Build the Workflow

### 1. Schedule Trigger
- **Node:** `n8n-nodes-base.scheduleTrigger`
- **Config:** Set your preferred interval (e.g., "Every Day at 06:00").
- This kicks off the entire pipeline automatically.

### 2. Create Sheet
- **Node:** `n8n-nodes-base.googleSheets` (v4)
- **Operation:** `create`
- **Document ID:** Your master spreadsheet ID
- **Title Expression:** `={{ $now.format('yyyy-MM-dd') }}`
- **Credentials:** Google Sheets OAuth2
- **Output:** Returns the new `sheetId` — critical for the Append step.

### 3. Get Queries
- **Node:** `n8n-nodes-base.googleSheets` (v4)
- **Operation:** `read` (getAll)
- **Document ID:** Same master spreadsheet
- **Sheet Name:** `Keywords` (the tab holding your search terms, one per row, column header = `Keyword`)

### 4. Loop Over Queries
- **Node:** `n8n-nodes-base.splitInBatches` (v3)
- **Batch Size:** 1 (process one keyword per loop iteration)
- **Connect:** Output 0 → back to Loop (for next batch), Output 1 → ScrapeHero

### 5. ScrapeHero — **The Critical Node**
- **Node:** `n8n-nodes-scrapehero.scrapeHero` (v1) — *the dedicated ScrapeHero node, not HTTP Request*
- **Credentials:** ScrapeHero API (add your API key in n8n credentials)
- **Parameters:**
  ```json
  {
    "apiSelection": "Amazon Search API",
    "textInput": "{{ $json.Keyword }}",
    "countryCode": "US",
    "pages": 4
  }
  ```
- **Output Fields to Map:** `query`, `search_results`, `next_page`

> **Why the dedicated node?** It handles pagination, retries, and ScrapeHero-specific error codes natively. No manual header wrangling.

### 6. Split Out Results
- **Node:** `n8n-nodes-base.itemLists` (v1)
- **Field to Split Out:** `search_results`
- This turns the API's array of 20+ products into individual n8n items for downstream filtering.

### 7. Filter Has Both Prices
- **Node:** `n8n-nodes-base.filter` (v2)
- **Conditions (AND combinator):**
  - `sale_price` **exists** (not empty)
  - `regular_price` **exists** (not empty)
- Only products with a *real* discount pass through.

### 8. Edit Fields (Map + Calculate)
- **Node:** `n8n-nodes-base.set` (v3.5)
- **Assignments:**
  | Output Field | Expression |
  |--------------|------------|
  | `ASIN` | `={{ $json.asin }}` |
  | `Name` | `={{ $json.name }}` |
  | `Sale Price` | `={{ $json.sale_price }}` |
  | `Regular Price` | `={{ $json.regular_price }}` |
  | `% OFF` | `={{ (($json.regular_price - $json.sale_price)/$json.regular_price*100).round(2) }}` |
  | `Product URL` | `={{ $json.product_url }}` |

- The `% OFF` formula computes: `((regular - sale) / regular) * 100`, rounded to 2 decimals.

### 9. Append to Sheet
- **Node:** `n8n-nodes-base.googleSheets` (v4)
- **Operation:** `append`
- **Document ID:** Same master spreadsheet
- **Sheet Name (Expression):** `={{ $('Create Sheet').item.json.sheetId }}` — dynamically targets today's tab
- **Columns:** Auto-map or define schema matching the 6 fields above
- **Key Setting:** Ensure `ASIN` is marked as a matching column if you later switch to `appendOrUpdate` for deduplication.

---

## Test the Workflow

### First Run (Full Backfill)
1. Populate the **Keywords** tab with 5–10 test queries (e.g., "smart watches", "wireless headphones", "robot vacuum").
2. Execute workflow manually in n8n (▶️ Execute Workflow).
3. Check the new dated sheet — each keyword should produce rows with ASIN, Name, prices, % OFF, URL.
4. Verify: no rows where `regular_price` is empty (filter works).

### Subsequent Runs (Incremental Updates)
- The Schedule Trigger runs automatically.
- Each run creates a **new dated sheet** — historical snapshots preserved.
- To deduplicate across runs, switch **Append to Sheet** → `appendOrUpdate` with `ASIN` as the matching column.

---

## How This Workflow Helps Your Business

| Benefit | Impact |
|---------|--------|
| **Zero manual checking** | Eliminates hours of daily price scraping |
| **Historical discount log** | Date-segregated sheets = trend analysis ready |
| **Scalable keyword coverage** | Add 100+ keywords to Keywords tab — no workflow changes |
| **Real discount detection** | Filter ensures only genuine price drops (not just "sale" badges) |
| **Affiliate/competitor intel** | Track rival pricing, spot lightning deals, feed deal sites |
| **API reliability** | ScrapeHero handles CAPTCHAs, IP rotation, parser maintenance |

---

## Best Practices

- **Do:** Keep keywords specific ("sony wh-1000xm5" > "headphones") for cleaner results.
- **Do:** Run on a schedule aligned with Amazon's deal cycles (early morning US time).
- **Do:** Monitor ScrapeHero credit usage — 4 pages × N keywords × daily runs adds up.
- **Don't:** Use generic HTTP Request for ScrapeHero — you'll reinvent pagination/error handling.
- **Don't:** Skip the `Filter Has Both Prices` step — pollutes sheets with non-deals.
- **Don't:** Hardcode the sheet name in Append — use the expression from Create Sheet.

---

## Ways to Extend the Workflow

- **Price Drop Alerts:** Add an IF node after Edit Fields → if `% OFF > 20` → Send Slack/Email/Telegram notification.
- **Stale Deal Cleanup:** Add a Merge (keepNonMatches) + Sort (row_number DESC) + Delete row for ASINs no longer discounted.
- **Multi-Country:** Duplicate ScrapeHero node per countryCode (US, CA, UK, DE) → union results.
- **Dashboard Feed:** Connect Google Sheets to Looker Studio, Power BI, or n8n's own Chart node.
- **ASIN Enrichment:** Pipe ASINs to ScrapeHero **Amazon Product API** for specs, images, reviews.
- **Competitor Tracking:** Add a "Competitor ASIN" column in Keywords tab → filter results to only those ASINs.

---

## Wrapping Up

You now have a **production-grade n8n Amazon Discount Tracker** that:
- Runs on autopilot via Schedule Trigger
- Uses ScrapeHero's purpose-built Amazon Search API node
- Filters for *real* discounts (both prices present)
- Stores daily snapshots in Google Sheets with ASIN-level deduplication
- Scales from 5 to 5,000 keywords without workflow changes

**Next step:** Deploy to n8n cloud or your self-hosted instance, hook up credentials, and watch the first dated sheet populate tomorrow morning.

---

> **Ready to automate your Amazon intelligence?**  
> 👉 [Try ScrapeHero's Amazon Search API free](https://www.scrapehero.com/amazon-search-api/) — 1,000 credits on us.  
> 👉 Explore more workflows: [Amazon Deal Scraping](https://www.scrapehero.com/amazon-deal-scraping/) | [Build a Price Tracker](https://www.scrapehero.com/how-to-build-a-price-tracker/) | [Price Monitoring Dashboard](https://www.scrapehero.com/build-price-monitoring-dashboard/) | [Amazon Lightning Deals](https://www.scrapehero.com/amazon-lightning-deals/)

---

*Built with n8n + ScrapeHero. Questions? Drop them in the comments or ping us on [Discord](https://discord.gg/scrapehero).*