# N8n Amazon Keyword Rank Tracker [Track Rankings Automatically]

## Introduction
If you are an Amazon seller or agency, monitoring where your products rank for critical keywords is essential to staying ahead of the competition. But manually searching Amazon and recording ranks is tedious and unsustainable. 

In this guide, we will show you how to build a powerful **n8n Amazon keyword rank tracker** to track Amazon ranking automatically. By combining the visual automation platform n8n with the ScrapeHero Amazon Search API, you can build a reliable Amazon search position tracker that pulls the latest keyword data, compares it to your existing records, and updates a Google Sheet—all on autopilot. 

## What the Workflow Does
This n8n rank tracking workflow automates the entire process of tracking Amazon search rankings. Here is the step-by-step logic:
1. **Fetch Keywords**: It reads a list of target keywords from a Google Sheet.
2. **Loop & Scrape**: It loops through each keyword, using the ScrapeHero node to fetch live Amazon search results.
3. **Data Formatting**: It extracts the `search_results` array and maps the API data into clean, business-friendly columns.
4. **Compare Data**: It pulls existing listings from your Google Sheet and compares them against the new data to find which listings are outdated.
5. **Upsert & Clean**: It updates existing rows, adds new products, and safely deletes the old, stale listings from the sheet.

## Before You Automate
Before diving into n8n, there are a few prerequisites and important considerations:
* **Accounts Needed**: You will need an n8n workspace, a Google Sheets account with OAuth2 credentials configured, and a [ScrapeHero account](https://www.scrapehero.com/amazon-scraping-services/) for API access.
* **Account Safety & ToS**: Web scraping Amazon directly from your own IP addresses (especially those tied to your Seller Central account) can quickly trigger CAPTCHAs, rate limits, and even account bans. It is highly recommended to use a third-party API like ScrapeHero, which handles proxy rotation and CAPTCHA solving for you.

## Overview
This workflow uses a sequence of 10 nodes to extract, transform, and load the data. It utilizes Google Sheets nodes for database operations, a Loop (Split in Batches) node for iteration, the ScrapeHero node for data extraction, and several core n8n nodes (Split Out, Merge, Set, Sort) to process the JSON datasets reliably.

## Build the Workflow

### Step 1: Get Queries
Start with a **Google Sheets** node named "Get Queries". Configure it to read your "Keyword Tracker" sheet to pull in the list of target keywords you want to monitor.

### Step 2: Loop Over Items
Add a **Loop (Split In Batches)** node. This ensures that the workflow processes one keyword at a time, preventing rate limit issues and keeping the data organized.

### Step 3: Fetch Data with ScrapeHero
Next, add the **ScrapeHero** node. 
* Set the API to **Amazon Search**.
* For the keyword parameter, use a loop variable. **Crucial Tip**: Do not rely on `$json.query` downstream. Instead, use expressions like `{{ $('Loop Over Items').item.json.Keywords }}` to reliably access the loop's current state.

### Step 4: Prepare New Items
The API returns a JSON object with a `search_results` array containing items like `asin`, `rank`, `name`, `sale_price`, and `product_url`. Add an **Item Lists (Split Out)** node targeting the `search_results` field to output each product as its own n8n item.

### Step 5: Format the Data
Amazon APIs return raw `snake_case` data. Use an **Edit Fields (Set)** node to map these fields to clean, `Title Case` column names before pushing to Google Sheets. For example, map `{{ $json.sale_price }}` to `Sale Price` and `{{ $json.review_count }}` to `Review Count`.

### Step 6: Get Existing Listings & Diff the Datasets
To update your sheet efficiently without creating duplicates, you need to compare the live data with your existing data.
1. Add a **Google Sheets** node to read the existing listings for the current keyword.
2. Add a **Merge** node to compare the two datasets. Set it to `mode: combine` and `joinMode: keepNonMatches`, merging by the `ASIN` field. This is the safest way to find old items without relying on heavy Code nodes.

### Step 7: Upsert and Delete
* Add a **Google Sheets** node set to **Upsert (Append or Update)** to insert the fresh data, matching on the `ASIN` column.
* To remove the outdated items identified by the Merge node, use a Google Sheets node set to **Delete**. 
* **The Bottom-Up Deletion Rule (CRITICAL)**: Before the Delete node, you MUST insert a **Sort node** to sort the items by `row_number` in `descending` order. Deleting top-down causes row-shifting bugs in Google Sheets!

## Test the Workflow
Once all credentials are in place and nodes are connected, click **Execute Workflow**. Watch the execution flow through the loop, pull data via the ScrapeHero API, and magically update your Google Sheet with the latest keyword rankings.

## How this Workflow Helps Your Business
Implementing an n8n Amazon keyword rank tracker provides a data-driven edge. Instead of paying for expensive, rigid SaaS tracking tools, you own the infrastructure. You can track unlimited keywords, customize the data you store, and create a historical database of your niche to spot trends, monitor competitors, and optimize your PPC campaigns.

## Best Practices
To ensure this n8n web scraping workflow runs flawlessly, keep these internal engineering best practices in mind:
* **Diffing Datasets Safely**: Always use the built-in Merge node for comparing new vs. old datasets instead of writing custom JavaScript. It is more robust and memory-efficient.
* **The Bottom-Up Deletion Rule**: Never delete rows from a spreadsheet starting from row 2 downwards. Always sort by row number descending and delete from the bottom up.
* **Loop Variable Management**: When iterating over pages of API results, always reference the loop node explicitly (e.g., `$('Loop Node Name').item.json`) rather than standard `$json` variables to avoid referencing the wrong context.
* **Business-Friendly Data Formatting**: Clean up the data mid-flight. Standardizing to `Title Case` headers makes the output much easier for stakeholders to read.
* **Handle Rate Limits**: Even robust APIs have throttling. If you are scraping hundreds of keywords, consider adding wait/delay nodes inside your loop.

## Ways to Extend the Workflow
Once the core Amazon rank tracking API workflow is running, consider adding:
* **Rank Drop Alerts**: How do I set up a rank drop alert in n8n? Add an If node after your Merge node. If a key product's rank drops below page 1, send an instant Slack or email notification.
* **Historical Tracking**: Instead of just updating and deleting, append the daily rank to a separate "History" sheet. How do I store Amazon keyword rank history in Google Sheets? Simply add a Google Sheets 'Append' node bypassing the delete logic.
* **Competitor Monitoring**: Use [ScrapeHero's Amazon Product API](https://www.scrapehero.com/marketplace/amazon-search-api/) to expand the workflow and track changes to competitor prices and reviews.

## Wrapping Up
Building your own n8n Amazon scraper is one of the most cost-effective ways to [track Amazon ranking automatically](https://www.scrapehero.com/data-driven-amazon-ranking/). By leveraging n8n's visual logic and [ScrapeHero's reliable APIs](https://www.scrapehero.com/amazon-scraping-apis/), you can bypass the [common web scraping challenges](https://www.scrapehero.com/amazon-web-scraping-challenges/) and focus on what matters: growing your Amazon business.

Ready to take control of your data? [Start automating Amazon product scraping with n8n and ScrapeHero today!](https://www.scrapehero.com/automate-amazon-product-scraping-with-n8n-and-scrapehero/)
