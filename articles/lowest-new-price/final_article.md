---
title: "Find the Lowest Offer Price on Amazon with n8n [Automated Price Tracker]"
seo_title: "Find the Lowest Offer Price on Amazon with n8n [Step-by-Step Workflow]"
meta_description: "Build an automated n8n web scraping workflow using the Amazon Offer Listing API and Google Sheets to find and monitor the lowest price across all sellers."
category: "ScrapeHero Cloud Resources > n8n"
---

# Find the Lowest Offer Price on Amazon with n8n [Automated Price Tracker]

Monitoring competitor pricing on Amazon requires tracking every seller offer across the catalog, not just the featured Buy Box. When teams find the lowest offer price on Amazon with n8n, manual catalog checks disappear and real-time market minimums sync directly into internal tracking sheets. Automated data pipelines remove guesswork, giving commercial teams complete visibility into third-party merchant discounts across multiple ASINs simultaneously.

Amazon's Buy Box algorithm prioritizes factors like Prime fulfillment status, customer feedback scores, and regional inventory proximity over sheer product price. Because of this weighting, third-party merchants fulfilling orders independently often undercut the Buy Box holder by significant margins without winning the featured spot. This guide demonstrates how to construct an n8n web scraping workflow using the Amazon Offer Listing API and n8n Google Sheets automation to capture all seller listings, parse raw pricing, isolate the cheapest new offer, and update catalog records automatically.

## Key Takeaways

- [Why does the Amazon Buy Box fail to reflect the true lowest market price?](#why-the-buy-box-does-not-always-reflect-the-lowest-price)
- [What prerequisites and sheet schemas are required before building?](#before-you-begin)
- [How do you construct the complete n8n workflow node by node?](#build-the-workflow)
- [How do you test execution and verify updated Google Sheets records?](#test-the-workflow)
- [How do you resolve the lexicographical sorting trap and filter by condition?](#common-pitfalls-sorting-and-condition-filtering)
- [What business use cases does multi-seller offer tracking serve?](#business-use-cases-for-tracking-amazon-offer-prices)
- [What direct enhancements can you add to scale this workflow?](#ways-to-extend-the-workflow)

---

## Table of Contents

- [Why the Buy Box Does Not Always Reflect the Lowest Price](#why-the-buy-box-does-not-always-reflect-the-lowest-price)
- [Before You Begin](#before-you-begin)
- [Build the Workflow](#build-the-workflow)
  - [Step 1: Add the Manual Trigger Node](#step-1-add-the-manual-trigger-node)
  - [Step 2: Read ASINs from Google Sheets](#step-2-read-asins-from-google-sheets)
  - [Step 3: Process ASINs Sequentially with Loop Over Items](#step-3-process-asins-sequentially-with-loop-over-items)
  - [Step 4: Fetch Marketplace Offers with the ScrapeHero Node](#step-4-fetch-marketplace-offers-with-the-scrapehero-node)
  - [Step 5: Unpack Offers with the Split Out Node](#step-5-unpack-offers-with-the-split-out-node)
  - [Step 6: Standardize Prices with the Edit Fields Node](#step-6-standardize-prices-with-the-edit-fields-node)
  - [Step 7: Sort Offers to Identify the Lowest Price](#step-7-sort-offers-to-identify-the-lowest-price)
  - [Step 8: Update Google Sheets with Lowest Price and Upstream Data](#step-8-update-google-sheets-with-lowest-price-and-upstream-data)
  - [Step 9: Close the Execution Loop](#step-9-close-the-execution-loop)
- [Test the Workflow](#test-the-workflow)
- [Common Pitfalls: Sorting and Condition Filtering](#common-pitfalls-sorting-and-condition-filtering)
  - [The Lexicographical Sorting Trap](#the-lexicographical-sorting-trap)
  - [Condition Filtering: Distinguishing New vs. Used Offers](#condition-filtering-distinguishing-new-vs-used-offers)
  - [Developer Pro-Tip: Pin Data to Preserve API Credits](#developer-pro-tip-pin-data-to-preserve-api-credits)
- [Business Use Cases for Tracking Amazon Offer Prices](#business-use-cases-for-tracking-amazon-offer-prices)
- [Ways to Extend the Workflow](#ways-to-extend-the-workflow)
  - [Send Instant Price Drop Alerts via Slack or Email](#send-instant-price-drop-alerts-via-slack-or-email)
  - [Schedule Automated Daily Execution with a Cron Trigger](#schedule-automated-daily-execution-with-a-cron-trigger)
  - [Filter Out Low-Rated Third-Party Sellers](#filter-out-low-rated-third-party-sellers)
  - [Calculate Margin Spreads Against Internal Wholesale Costs](#calculate-margin-spreads-against-internal-wholesale-costs)
- [Wrapping Up](#wrapping-up)
- [Frequently Asked Questions](#frequently-asked-questions)

---

## Why the Buy Box Does Not Always Reflect the Lowest Price

Many e-commerce teams assume that tracking an Amazon product page means tracking the Buy Box. Amazon's Buy Box (also known as the Featured Offer) is not a simple lowest-price display. The platform awards the Buy Box through a proprietary algorithm that weights Fulfillment by Amazon (FBA) eligibility, Prime shipping speed, seller feedback ratings, return history, and geographic inventory distribution.

As a direct consequence, the merchant holding the Buy Box is frequently 5% to 30% more expensive than competing third-party sellers listed on the "All Offers" tab (`/gp/offer-listing/`). Merchant-fulfilled (FBM) sellers, new store launches, and liquidators routinely undercut the Buy Box price. If your business tracks only the featured price, you miss the true market floor.

Amazon balances competitive price floors against seller performance metrics when calculating rank positions and Buy Box eligibility, as explored in [data-driven Amazon ranking](https://www.scrapehero.com/data-driven-amazon-ranking/) strategies. While brands often rely on an amazon rank tracking api or an amazon search position tracker to track amazon ranking automatically, monitoring keyword positions alone leaves out the pricing pressure created by competing sellers on individual ASINs. Combining an n8n rank tracking workflow with granular offer listing monitoring provides a complete picture of both organic search visibility and competitive pricing floors.

Capturing these secondary listings manually across hundreds of ASINs is practically impossible due to Amazon's anti-scraping defenses, pagination complexities, and dynamic layout changes. For deeper background on these technical hurdles, review [Amazon web scraping challenges](https://www.scrapehero.com/amazon-web-scraping-challenges/). Using specialized [Amazon scraping APIs](https://www.scrapehero.com/amazon-scraping-apis/) solves this bottleneck by returning structured JSON containing every seller, price, shipping cost, condition, and fulfillment method in a single request.

![Amazon Offer Listing Page Comparison](add-image-url)

---

## Before You Begin

Before assembling the pipeline in n8n, verify that all necessary credentials and tools are in place:

| Prerequisite | Purpose | Setup / Requirement |
| :--- | :--- | :--- |
| **Active n8n Instance** | Workflow automation engine | Self-hosted n8n (v1.0+) or an active n8n Cloud workspace |
| **ScrapeHero Community Node** | Amazon Offer Listing integration | Installed via **Settings > Community Nodes** (`n8n-nodes-scrapehero`) |
| **ScrapeHero API Key** | Authentication for marketplace scraping | Registered account on the [ScrapeHero Cloud Marketplace](https://www.scrapehero.com/marketplace/amazon-search-api/) |
| **Google Cloud OAuth Credentials** | Spreadsheet read/write permissions | Configured Google Sheets credential inside n8n |
| **Target Google Sheet** | Input catalog and output destination | Spreadsheet titled `Lowest New Price` with sheet tab `ASINs` |

Set up the header row in your `ASINs` tab with the following structure:

| Column Header | Example Entry | Description |
| :--- | :--- | :--- |
| `ASIN` | `B08141GQQG` | The unique product identifier. Serves as the primary matching key. |
| `Name` | `Logitech G733 LIGHTSPEED Headset` | The product title populated automatically by the workflow. |
| `Lowest New Price` | `$119.00` | The lowest detected price for items in New condition. |

![Google Sheet Setup for ASIN Tracking](add-image-url)

---

## Build the Workflow

The workflow reads ASINs from Google Sheets, loops through each product one by one, retrieves all active seller offers via ScrapeHero, unpacks the offer array, standardizes the price property, sorts the offers ascending, writes the cheapest price back to Google Sheets, and repeats. This modular n8n web scraping workflow provides full control over data transformation and rate management.

The diagram below outlines the complete execution sequence:

```text
[Manual Trigger]
       │
       ▼
  [Get ASINs] (Google Sheets)
       │
       ▼
┌─► [Loop Over Items] (Split In Batches)
│      │
│      ▼
│   [ScrapeHero] (Amazon Offer Listing API)
│      │
│      ▼
│   [Split Out] (Unpack offer_listings)
│      │
│      ▼
│   [Edit Fields1] (Isolate Price)
│      │
│      ▼
│   [Sort] (Sort Ascending by Price)
│      │
│      ▼
│   [Update Sheets] (Append or Update, Execute Once: true)
│      │
└──────┘
```

Follow these step-by-step instructions to configure each node.

### Step 1: Add the Manual Trigger Node

The manual trigger starts the workflow execution on demand during development and testing.

1. Click the **+** (plus) icon on the empty n8n canvas.
2. Type `Manual Trigger` in the search panel.
3. Select **On clicking 'execute'** (`n8n-nodes-base.manualTrigger`).
4. Keep the default configuration and position the node on the far left.

![Manual Trigger Node Setup](add-image-url)

### Step 2: Read ASINs from Google Sheets

This node retrieves your list of target products from your spreadsheet.

1. Click the plus icon on the output handle of the **Manual Trigger** node.
2. Search for `Google Sheets` and select it (`n8n-nodes-base.googleSheets`).
3. Set **Credential to connect with** to your configured Google Sheets OAuth account.
4. Set **Resource** to `Document` and **Operation** to `Get Many Rows` (or `Read Rows`).
5. Under **Document**, select `From list` and choose `Lowest New Price`.
6. Under **Sheet**, select `From list` and choose `ASINs`.
7. Rename the node to `Get ASINs`.
8. Click **Test step** to confirm that your list of ASIN rows is fetched into the canvas.

![Google Sheets Node Reading ASINs](add-image-url)

### Step 3: Process ASINs Sequentially with Loop Over Items

Processing product queries one item at a time avoids hitting third-party rate limits and prevents execution timeouts on large catalogs.

1. Click the plus icon on the output handle of **Get ASINs**.
2. Search for `Loop Over Items` (also named `Split In Batches`, `n8n-nodes-base.splitInBatches`).
3. Set **Batch Size** to `1`.
4. Keep other options default and rename the node to `Loop Over Items`.

This node provides two output handles: the top handle (`loop`) executes for each item in the batch, and the bottom handle (`done`) triggers after all items finish processing.

![Loop Over Items Node Configuration](add-image-url)

### Step 4: Fetch Marketplace Offers with the ScrapeHero Node

The ScrapeHero node queries the Amazon Offer Listing API for the current ASIN in the loop. Rather than coding custom headless browsers or wrestling with anti-bot shields, deploying the dedicated ScrapeHero community node as your n8n Amazon scraper keeps canvas logic clean and handles request execution reliably.

1. Connect the top output handle of **Loop Over Items** to a new node.
2. Search for `ScrapeHero` (`n8n-nodes-scrapehero.scrapeHero`).
3. Select your pre-configured **ScrapeHero API** credential.
4. In the **API** dropdown, select `Amazon Offer Listing` (`amazonOfferListing`).
5. In the **ASIN** parameter field, switch to the expression editor and enter:

```javascript
={{ $json.ASIN }}
```

6. Click **Test step** to execute the request for the first ASIN.

The API returns top-level metadata including `asin`, `product_title`, `product_rating`, `product_ratings_count`, and an array named `offer_listings` containing every active seller offer. For automated catalog scraping patterns, refer to [automating Amazon product scraping with n8n and ScrapeHero](https://www.scrapehero.com/automate-amazon-product-scraping-with-n8n-and-scrapehero/).

![ScrapeHero Node Querying Amazon Offer Listing API](add-image-url)

### Step 5: Unpack Offers with the Split Out Node

The `offer_listings` property contains an array of seller objects nested inside a single incoming item. To filter and sort individual offers, convert each array element into a standalone n8n item.

1. Click the plus icon on the output handle of the **ScrapeHero** node.
2. Search for `Split Out` (`n8n-nodes-base.splitOut`).
3. In the **Field to Split Out** parameter, enter:

```text
offer_listings
```

4. Click **Test step**.

The output panel transforms from 1 product item into multiple items (for example, 11 individual offer items), each containing `price`, `condition`, `seller`, `ships_from`, and `fulfilled_by_amazon`.

![Split Out Node Unpacking Array](add-image-url)

### Step 6: Standardize Prices with the Edit Fields Node

The Edit Fields (Set) node extracts and formats the pricing property for downstream operations.

1. Click the plus icon on the output handle of the **Split Out** node.
2. Search for `Edit Fields` (`n8n-nodes-base.set`).
3. In the **Fields to Set** section, click **Add Value** and select `String`.
4. Set **Name** to `Price`.
5. Set **Value** to the expression:

```javascript
={{ $json.price }}
```

6. Rename this node to `Edit Fields1`.
7. Click **Test step** to confirm the extracted field.

![Edit Fields Node Isolating Price](add-image-url)

### Step 7: Sort Offers to Identify the Lowest Price

Sorting the items ascending by price places the cheapest marketplace offer at the very top (index 0).

1. Click the plus icon on the output handle of **Edit Fields1**.
2. Search for `Sort` (`n8n-nodes-base.sort`).
3. Under **Sort Fields**, click **Add Field**.
4. In **Field Name**, enter `Price`.
5. Set **Order** to `Ascending`.
6. Click **Test step**.

The item list reorders, placing the lowest price at item index 0.

![Sort Node Ordering Offers Ascending](add-image-url)

### Step 8: Update Google Sheets with Lowest Price and Upstream Data

This step writes the verified lowest price back to Google Sheets. Because the goal is to record only the cheapest offer, instruct n8n to execute this node once for the first item in the list rather than once per offer. Configuring this n8n Google Sheets automation node ensures rows update in place without creating duplicate records or overwriting cells with higher-priced offers.

1. Click the plus icon on the output handle of the **Sort** node.
2. Search for `Google Sheets` (`n8n-nodes-base.googleSheets`).
3. Set **Operation** to `Append or Update Row` (`appendOrUpdate`).
4. Select the `Lowest New Price` document and the `ASINs` sheet tab.
5. Set **Mapping Mode** to `Define Below`.
6. In **Matching Columns**, select `ASIN`. This setting ensures rows update in place without creating duplicate entries.
7. Click the node's **Settings** tab (the gear icon) and toggle **Execute Once** to `true` (ON). This prevents n8n from running on all offer items and overwriting the sheet with higher-priced entries.
8. Switch back to the **Parameters** tab and map the columns:

- For **ASIN**, reference the upstream ScrapeHero node data:

```javascript
={{ $('ScrapeHero').item.json.asin }}
```

- For **Name**, reference the upstream product title:

```javascript
={{ $('ScrapeHero').item.json.product_title }}
```

- For **Lowest New Price**, map the sorted price from the current item:

```javascript
={{ $json.Price }}
```

9. Rename the node to `Update Sheets`.
10. Click **Test step**.

Notice how the expressions reference `$('ScrapeHero').item.json.asin` and `$('ScrapeHero').item.json.product_title`. Inside the loop branch after the Split Out node, individual items only retain offer-level properties. Referencing upstream nodes explicitly allows the workflow to inject top-level product attributes back into your spreadsheet.

![Google Sheets Node Mapping Lowest Price](add-image-url)

### Step 9: Close the Execution Loop

To ensure every ASIN in your initial spreadsheet is processed, connect the output of **Update Sheets** back to the input of **Loop Over Items**.

1. Click the output handle of the **Update Sheets** node.
2. Drag the connection line back to the input handle of the **Loop Over Items** node.

When execution finishes for an ASIN, n8n loops back to **Loop Over Items**, which increments the batch index, picks up the next product, and triggers the next scrape until all rows complete.

![Complete Loop Connection in n8n Canvas](add-image-url)

---

## Test the Workflow

To test the entire pipeline end-to-end:

1. Click **Test workflow** in the bottom panel of the n8n canvas.
2. Watch the execution progression across each node:
   - **Get ASINs** reads the ASIN list.
   - **Loop Over Items** activates and hands the first ASIN to **ScrapeHero**.
   - **ScrapeHero** fetches the offer listing payload.
   - **Split Out** expands the offers into individual items.
   - **Edit Fields1** isolates the price field.
   - **Sort** arranges offers ascending.
   - **Update Sheets** executes once to update the corresponding ASIN row.
   - The loop repeats until all ASINs are processed.
3. Open your Google Sheet. Verify that the `Name` column now displays the full product title and `Lowest New Price` contains the lowest recorded price.

![Verified Output in Google Sheets](add-image-url)

---

## Common Pitfalls: Sorting and Condition Filtering

### The Lexicographical Sorting Trap

A critical issue in API data processing is string comparison. In raw API responses, prices are strings formatted with currency signs, such as `"$119.48"`, `"$64.02"`, and `"$99.99"`.

If n8n sorts these values as plain text strings, it applies lexicographical (alphabetical) comparison. Because the character `"1"` comes before `"6"` in ASCII encoding:

```text
"$119.48" < "$64.02"  // Evaluates to true in string comparison
```

Under lexicographical sorting, `"$119.48"` sorts before `"$64.02"`. If this occurs, the workflow will mistakenly label `$119.48` as the lowest price.

To avoid this trap, convert the price string to a pure numerical float in the **Edit Fields1** node before passing it to the Sort node:

```javascript
={{ Number($json.price.replace(/[^0-9.]/g, '')) }}
```

Alternatively, change the property type to `Number` in the Set node. This guarantees that mathematical sorting evaluates `$64.02` as lower than `$119.48`.

### Condition Filtering: Distinguishing New vs. Used Offers

Marketplace sellers list items in varying conditions, including `"New"`, `"Used - Like New"`, `"Used - Very Good"`, and `"Refurbished"`.

In the sample API response for Logitech Headset (`B08141GQQG`), the absolute lowest prices on the listing are:
- Position 2: `$64.02` (`Used - Very Good`, Amazon Resale)
- Position 3: `$66.02` (`Used - Like New`, Amazon Resale)
- Position 5: `$119.00` (`New`, HALF TIME)

If your workflow seeks the **Lowest New Price**, sorting without condition filtering selects `$64.02`. Comparing new inventory against open-box warehouse deals distorts pricing intelligence.

To enforce condition accuracy, insert a **Filter** node (`n8n-nodes-base.filter`) between **Split Out** and **Edit Fields1**:
- Set Condition: `{{ $json.condition }}` `equals` `New`.

This strips out used and refurbished listings before the sorting phase, ensuring you compare apples to apples.

### Developer Pro-Tip: Pin Data to Preserve API Credits

When building and debugging workflows in n8n, re-running the canvas repeatedly calls external APIs, consuming credits unnecessarily.

n8n includes a **Pin Data** feature:
1. Run the **ScrapeHero** node once to retrieve real output.
2. In the ScrapeHero node panel, click the pin icon in the upper-right corner of the output display.
3. Once pinned, the output payload stays cached locally inside the canvas.

You can modify expressions, adjust the Sort node, and re-test Google Sheets mappings as many times as needed without triggering additional external API requests. Unpin the node only when you are ready for production execution.

---

## Business Use Cases for Tracking Amazon Offer Prices

Tracking complete multi-seller offer listings rather than relying on surface Buy Box metrics provides substantial commercial value:

- **Dynamic Competitive Repricing Across Merchant-Fulfilled Offers:** Track third-party merchants who undercut the Buy Box through Merchant Fulfilled Network (MFN) channels to protect sales volume and calibrate automated repricing boundaries.
- **MAP Policy Enforcement and Unauthorized Reseller Detection:** Identify rogue third-party distributors and gray-market liquidators violating Minimum Advertised Price (MAP) thresholds across your brand's catalog.
- **Retail Arbitrage and Wholesale Margin Discovery:** Spot market price anomalies where secondary seller discounts create profitable arbitrage and inventory acquisition spreads.
- **Competitor Stock and Discounting Trend Analysis:** Monitor daily price floor movements in Google Sheets to anticipate competitor clearance cycles and promotional discounting schedules.
- **Buy Box Loss Early Warning Detection:** Identify when competing merchants introduce aggressive price drops before Amazon shifts the featured offer badge, giving operations teams time to respond.

---

## Ways to Extend the Workflow

### Send Instant Price Drop Alerts via Slack or Email

Add an **If** node after the **Sort** node that checks whether the detected lowest price falls below a predetermined price threshold (for example, `{{ $json.Price < 100 }}`). Connect the `true` output to a **Slack** or **Gmail** node to send real-time alerts directly to your merchandising team.

### Schedule Automated Daily Execution with a Cron Trigger

Replace the **Manual Trigger** node with a **Schedule Trigger** (`n8n-nodes-base.scheduleTrigger`). Configure the trigger to execute every morning at 06:00 UTC. This keeps your Google Sheets pricing database continuously synchronized without manual intervention.

### Filter Out Low-Rated Third-Party Sellers

In competitive intelligence, very low-rated sellers often represent fake listings or drop-shippers with extended delivery windows. Add an expression in your filtering stage to evaluate `{{ parseFloat($json.seller_rating) >= 4.0 }}` or verify `{{ $json.fulfilled_by_amazon === true }}` to track only reliable, Prime-eligible competitors.

### Calculate Margin Spreads Against Internal Wholesale Costs

Add an extra column to your input Google Sheet containing your landed wholesale unit cost (`Cost`). In the **Edit Fields** node, calculate the gross profit spread between the lowest marketplace price and your inventory cost:

```javascript
={{ ($json.Price - $('Get ASINs').item.json.Cost).toFixed(2) }}
```

This immediately surfaces whether you can profitably undercut the lowest current market offer.

---

## Wrapping Up

Building an automated Amazon lowest price tracker with n8n provides complete control over your marketplace intelligence. By bypassing the Buy Box to extract all active seller listings, standardizing price data, and updating Google Sheets in real time, commercial teams gain an accurate view of true market pricing without relying on rigid, expensive third-party SaaS tools.

To start collecting detailed Amazon seller listings, sign up for a [ScrapeHero Cloud account](https://www.scrapehero.com/marketplace/amazon-search-api/) and get your API credentials. Plug your key into the n8n ScrapeHero node to automate your price monitoring pipeline in minutes. Learn more about extraction options with the guide to [scraping Amazon product data](https://www.scrapehero.com/scrape-amazon-product-data/).

For organizations managing catalogs spanning hundreds of thousands of ASINs across international marketplaces, managing DIY automation infrastructure and handling enterprise-scale proxy infrastructure can demand dedicated engineering time. At ScrapeHero, we provide fully managed [enterprise web scraping services](https://www.scrapehero.com/amazon-scraping-services/) that handle proxy rotation, anti-bot bypass, custom data validation, and automated delivery directly to your data warehouse so your team can focus entirely on core strategy.

---

## Frequently Asked Questions

### How do you find the lowest offer price on Amazon instead of just the Buy Box?
To find the lowest offer price, you must access the Amazon Offer Listing page (`/gp/offer-listing/ASIN`), which enumerates all sellers for a product. Standard Amazon product detail pages only surface the Buy Box winner, which is often higher priced due to Prime delivery and seller rating weighting. Using ScrapeHero's Amazon Offer Listing API allows you to extract every seller offer programmatically into an automated pipeline.

### Can you scrape Amazon search results and offer listings with n8n without getting blocked?
Yes. You can scrape Amazon search results, product details, and offer listings using n8n. While basic HTTP request nodes frequently face IP blocks and CAPTCHA challenges, integrating the dedicated ScrapeHero community node routes requests through managed proxy networks and browser emulation systems, returning clean JSON without triggering anti-bot protections.

### What should you store if an ASIN returns no active offer listings?
If an ASIN is out of stock or has no active third-party sellers, the `offer_listings` array returns empty. You should place an **If** node checking `{{ $json.offer_listings.length > 0 }}` after the ScrapeHero node. If false, branch to a Google Sheets node that marks the status column as `Out of Stock` or records `N/A` for the lowest price.

### How often should you track Amazon offer prices and rankings with n8n?
For high-velocity categories like consumer electronics or toys, running the workflow every 2 to 4 hours captures intra-day price wars and flash sales. For stable, long-tail catalogs, a daily execution scheduled via the n8n Schedule Trigger at off-peak hours is generally sufficient to maintain price accuracy while conserving API credits. Synchronizing your price monitoring with an n8n rank tracking workflow helps correlate price movements directly with organic search placement.

### Why does n8n sort price strings incorrectly?
n8n sorts raw text fields lexicographically rather than numerically. Because strings like `"$119.48"` begin with `"1"`, they evaluate as smaller than `"$64.02"` in alphabetical ordering. You must strip currency symbols using a regular expression such as `{{ Number($json.price.replace(/[^0-9.]/g, '')) }}` to ensure the Sort node compares numbers mathematically.

### Is scraping Amazon product and pricing data legal?
Publicly available Amazon data such as product titles, seller listings, and offer prices can generally be scraped legally, provided the scraper extracts publicly accessible information without bypassing authentication barriers or violating copyright. Using compliant, specialized scraping APIs like ScrapeHero ensures your workflow gathers public market data ethically while managing rate limits and infrastructure responsibly.
