# n8n Amazon Keyword Rank Tracker [Track Rankings Automatically]

## Introduction
Monitoring where your products rank for critical keywords is essential for any Amazon seller or agency striving to stay ahead of the competition. Manually searching Amazon and recording ranks, however, is a tedious and unsustainable process. 

This guide shows how to build a powerful **n8n Amazon keyword rank tracker** to track Amazon ranking automatically. By combining the visual automation platform n8n with the ScrapeHero Amazon Search API, you can build a reliable Amazon search position tracker that pulls the latest keyword data, compares it to your existing records, and updates a Google Sheet—all on autopilot. 

## Key Takeaways
* How do I build an Amazon keyword rank tracker in n8n?
* What is the best Amazon search scraper API for n8n?
* How do I extract the rank field from Amazon Search API results?
* What should I store if my ASIN isn't in the results?
* Should I count sponsored results when tracking Amazon rank?
* How do I set up a rank drop alert in n8n?
* How do I store Amazon keyword rank history in Google Sheets?

## What the Workflow Does
This n8n rank tracking workflow automates the entire process of tracking Amazon search rankings. Here is the step-by-step logic:
1. **Fetch Keywords**: It reads a list of target keywords from a Google Sheet.
2. **Loop & Scrape**: It loops through each keyword, using the ScrapeHero node to fetch live Amazon search results.
3. **Data Formatting**: It extracts the `search_results` array and maps the API data into clean, business-friendly columns.
4. **Compare Data**: It pulls existing listings from your Google Sheet and compares them against the new data to find which listings are outdated.
5. **Upsert & Clean**: It updates existing rows, adds new products, and safely deletes old, stale listings from the sheet.

## Before You Automate
Before diving into n8n, there are a few prerequisites and important considerations:
* **Accounts Needed**: You will need an n8n workspace, a Google Sheets account with OAuth2 credentials configured, and a [ScrapeHero account](https://www.scrapehero.com/amazon-scraping-services/) for API access.
* **Account Safety & ToS**: Web scraping Amazon directly from your own IP addresses can quickly trigger CAPTCHAs, rate limits, and even account bans. It is highly recommended to use a third-party API like ScrapeHero, which handles proxy rotation and CAPTCHA solving for you.

## How do I build an Amazon keyword rank tracker in n8n?
This workflow uses a sequence of 10 nodes to extract, transform, and load the data. It utilizes Google Sheets nodes for database operations, a Loop (Split in Batches) node for iteration, the ScrapeHero node for data extraction, and several core n8n nodes (Split Out, Merge, Set, Sort) to process the JSON datasets reliably.

### Step 1: Get Queries
Start by adding a Google Sheets node. Click the '+' button in the n8n canvas, search for 'Google Sheets', and select the node. Name it "Get Queries". Configure it to read your "Keyword Tracker" sheet to pull in the list of target keywords you want to monitor. Select the appropriate spreadsheet and worksheet in the node settings.

### Step 2: Loop Over Items
Click the '+' button in the n8n canvas, search for 'Loop', and select the **Loop (Split In Batches)** node. Connect it to your Google Sheets node. This ensures that the workflow processes one keyword at a time, preventing rate limit issues and keeping the data organized.

### Step 3: What is the best Amazon search scraper API for n8n?
The best Amazon search scraper API for n8n is ScrapeHero because it provides seamless integration and handles all anti-scraping mechanisms automatically. Click the '+' button in the n8n canvas, search for 'ScrapeHero', and select the node. Connect it inside your loop.
* Set the API to **Amazon Search**.
* For the keyword parameter, use a loop variable. **Crucial Tip**: Use expressions like `={{ $json.Keywords }}` as demonstrated in the workflow. You can do this by clicking the gear icon next to the field and selecting 'Add Expression'.

### Step 4: How do I extract the rank field from Amazon Search API results?
The API returns a JSON object with a `search_results` array containing items like `asin`, `rank`, `name`, `sale_price`, and `product_url`. Click the '+' button in the n8n canvas, search for 'Item Lists', and select the **Item Lists (Split Out)** node. Name it "Prepare New Items". Set the 'Field To Split Out' to `search_results` to output each product as its own n8n item. Connect it after the ScrapeHero node.

### Step 5: Format the Data
Amazon APIs return raw `snake_case` data. Click the '+' button in the n8n canvas, search for 'Set', and select the **Set** node. Name it "Edit Fields". Connect it to your Item Lists node. Use this node to map these fields to clean, `Title Case` column names before pushing to Google Sheets. Click 'Add Value' for each field. For example, map the value `={{ $json.sale_price }}` to the name `Sale Price` and `={{ $json.review_count }}` to `Review Count`.

### Step 6: Get Existing Listings & Diff the Datasets
To update your sheet efficiently without creating duplicates, you need to compare the live data with your existing data.
1. Click the '+' button, search for 'Google Sheets', and select it. Connect it to your previous node. Configure it to read the existing listings for the current keyword.
2. Click the '+' button, search for 'Merge', and select the **Merge** node. Name it "Find Old Items". Connect the new data and the existing data into the two inputs of the Merge node. Set it to `mode: combine` and `joinMode: keepNonMatches`, merging by the `ASIN` field. This is the safest way to find old items without relying on heavy Code nodes.

### Step 7: Upsert and Delete
* Click the '+' button, search for 'Google Sheets', and select it. Set the operation to **Upsert (Append or Update)** to insert the fresh data, matching on the `ASIN` column. Connect this to the main output of your data flow.
* To remove the outdated items identified by the Merge node, use a Google Sheets node set to **Delete**. Connect it to the unmatched output of the Merge node.
* **The Bottom-Up Deletion Rule (CRITICAL)**: Before the Delete node, you MUST insert a **Sort node**. Click the '+' button, search for 'Sort', and select it. Set it to sort the items by `row_number` in `descending` order. Deleting top-down causes row-shifting bugs in Google Sheets!

## Common Rank Tracking Questions

### What should I store if my ASIN isn't in the results?
If an ASIN drops out of the top results entirely, the most effective approach is to retain the historical data and log a default "unranked" value (such as a rank of 0 or >100) to maintain accurate trend tracking without skewing your primary performance metrics.

### Should I count sponsored results when tracking Amazon rank?
When evaluating true organic visibility, sponsored results are typically excluded because they are paid placements. However, tracking both can be highly valuable to understand overall share of voice and competitor ad strategies. ScrapeHero allows you to distinguish between organic and sponsored listings within the API payload.

## Test the Workflow
Once all credentials are in place and nodes are connected, trigger the execution by clicking the 'Execute Workflow' button at the bottom of the canvas. Watch the execution flow through the loop, pull data via the ScrapeHero API, and seamlessly update your Google Sheet with the latest keyword rankings.

## How this Workflow Helps Your Business
Implementing an n8n Amazon keyword rank tracker provides a data-driven edge. Instead of paying for expensive, rigid SaaS tracking tools, you own the infrastructure. You can track unlimited keywords, customize the data you store, and create a historical database of your niche to spot trends, monitor competitors, and optimize your PPC campaigns.

## Best Practices
To ensure this n8n web scraping workflow runs flawlessly, keep these internal engineering best practices in mind:
* **Diffing Datasets Safely**: Always use the built-in Merge node for comparing new vs. old datasets. It is robust and memory-efficient.
* **The Bottom-Up Deletion Rule**: Never delete rows from a spreadsheet starting from row 2 downwards. Always sort by row number descending and delete from the bottom up.
* **Handle Rate Limits**: Even robust APIs have throttling. If you are scraping hundreds of keywords, ensure proper delay management.

## Ways to Extend the Workflow
Once the core Amazon rank tracking API workflow is running, consider adding:
* **How do I set up a rank drop alert in n8n?** Add an If node after your Merge node by clicking the '+' button and selecting 'If'. If a key product's rank drops below page 1, route the output to a Slack or Email node to send an instant notification.
* **How do I store Amazon keyword rank history in Google Sheets?** Instead of just updating and deleting, append the daily rank to a separate "History" sheet. Simply add a Google Sheets 'Append' node bypassing the delete logic.
* **Competitor Monitoring**: Use [ScrapeHero's Amazon Product API](https://www.scrapehero.com/marketplace/amazon-search-api/) to expand the workflow and track changes to competitor prices and reviews.

## Wrapping Up
Building your own n8n Amazon scraper is one of the most cost-effective ways to [track Amazon ranking automatically](https://www.scrapehero.com/data-driven-amazon-ranking/). By leveraging n8n's visual logic and [ScrapeHero's reliable APIs](https://www.scrapehero.com/amazon-scraping-apis/), you can bypass the [common web scraping challenges](https://www.scrapehero.com/amazon-web-scraping-challenges/) and focus on what matters: growing your Amazon business.

Ready to take control of your data? [Start automating Amazon product scraping with n8n and ScrapeHero today!](https://www.scrapehero.com/automate-amazon-product-scraping-with-n8n-and-scrapehero/)
