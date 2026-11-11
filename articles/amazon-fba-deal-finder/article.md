[SEO Meta]
Focus Keyword: Amazon FBA deals monitoring
SEO Title: Automating Amazon FBA Deals Monitoring Using n8n [Step-by-Step Workflow]
SEO Description: Automate Amazon FBA deals monitoring using n8n and ScrapeHero API. Track seller offers, detect competition changes, and receive instant alerts.
[/SEO Meta]

# How to Monitor Amazon FBA Deals With n8n and ScrapeHero

Tracking Fulfillment by Amazon (FBA) deals manually across expanding product catalogs is time-consuming and prone to delays. Setting up automated **Amazon FBA deals monitoring** with n8n ensures that changes in prime-eligible seller competition, stock sellouts, and new offer surges are detected immediately without manual oversight.

This tutorial shows how to build an n8n workflow that:

1. Reads tracked ASINs and previous FBA offer counts from Google Sheets  
2. Retrieves live seller offers through ScrapeHero's Amazon Offer Listing API  
3. Filters for active FBA offers and computes the current deal count  
4. Compares counts to suppress duplicate alerts, logs updates to Google Sheets, and sends alerts to Google Chat  

[inlinelink]

### What You’ll Learn

* How to configure automated Amazon FBA deals monitoring using n8n and ScrapeHero.  
* How to use the Amazon Offer Listing API to extract real-time seller and fulfillment details.  
* How to iterate over a list of ASINs and process each catalog entry individually.  
* How to unpack nested `offer_listings` arrays into discrete item streams.  
* How to filter exclusively for prime-eligible offers where `fulfilled_by_amazon` is true.  
* How to dynamically calculate the number of active FBA sellers in an Edit Fields node.  
* How to stop receiving duplicate alerts by validating current counts against baseline figures.  
* How to append updated counts to Google Sheets and broadcast instant notifications to Google Chat.  

[/inlinelink]

## How Can You Use the Amazon Offer Listing API to Find FBA Deals?

Most e-commerce monitors look only at the featured Buy Box. While the Buy Box captures the majority of customer orders, it conceals critical competitive dynamics occurring across the wider catalog. Secondary FBA sellers often match or undercut the featured offer, while third-party merchant-fulfilled sellers fluctuate in price without prime shipping benefits.

When tracking high-demand products, changes in the number of active FBA sellers indicate market shifts:

- **Inventory exhaustion:** When FBA seller counts drop, competitors are running out of prime stock, allowing remaining sellers to raise prices.
- **New competition entering:** An abrupt jump in FBA count signals that wholesale distributors or arbitrageurs have checked in new inventory at fulfillment centers.
- **Buy Box suppression:** If all FBA sellers stock out, Amazon may suppress the Buy Box or hand it to a merchant-fulfilled seller with longer delivery estimates.

Extracting these details by hand or with fragile custom scripts runs into anti-bot barriers and layout variations. Using ScrapeHero's [Amazon scraping APIs](https://www.scrapehero.com/amazon-scraping-apis/) solves this challenge. The Amazon Offer Listing API returns structured JSON containing every seller, price, shipping origin, and fulfillment status in a single call. To understand broader catalog trends, explore how to [scrape Amazon product data](https://www.scrapehero.com/scrape-amazon-product-data/) and examine [scrape Amazon product offers and sellers](https://www.scrapehero.com/scrape-amazon-product-offers-and-sellers/).

## Before You Begin

Before building the Amazon FBA deals monitoring workflow, prepare the following resources:

1. An active n8n instance (cloud-hosted or self-hosted n8n installation).  
2. A Google Cloud OAuth client ID and client secret connected to Google Sheets.  
3. A Google Spreadsheet named **FBA Deal Finder** with a tab named **Sheet1**.  
4. A [ScrapeHero account and API key](https://app.scrapehero.com/docs/API-docs/authentication/).  
5. A Google Chat webhook or OAuth credential with access to your target alert space.  

Set up your Google Sheet with the following column headers and baseline tracking rows:

| ASIN | Product Name | Previous FBA Count |
| :--- | :--- | :--- |
| B08141GQQG | Logitech G733 LIGHTSPEED Wireless Gaming Headset | 3 |
| B07PXGQC1Q | Apple AirPods with Charging Case | 5 |

## Create the Workflow

### 1. Add a Schedule Trigger

Open the n8n canvas and start with a trigger node to schedule recurring runs.

Click the **plus icon**, search for **Schedule Trigger**, and add it to the canvas. Set the trigger interval according to your monitoring requirements (such as every day, every week, or once a month). A scheduled trigger ensures continuous catalog surveillance without manual activation.

![Searching and adding Schedule Trigger in an n8n workflow](images/Searching and adding Schedule Trigger in an n8n workflow.png)

### 2. Read Tracked Products and Baseline Counts from Google Sheets

Next, read your catalog ASINs and existing baseline counts into the workflow.

Add a **Google Sheets** node after the Schedule Trigger. Under **Operation**, choose **Get Row(s) in Sheet**. Connect your Google Sheets account and configure:

1. **Document:** Select `FBA Deal Finder` from the list.  
2. **Sheet:** Select `Sheet1`.  

Click **Execute Step** to verify that the rows with ASINs, product names, and baseline counts are loaded into n8n.

![Configuring the Google Sheets node to read ASINs](images/Configuring the Google Sheets node to read ASINs.png)

### 3. Process Each Product with Loop Over Items

Processing products one at a time ensures that API requests execute sequentially and avoids rate limits or memory exhaustion.

Add a **Loop Over Items** node after the Google Sheets node. Keep the default **Batch Size** set to `1`. The loop node routes each product through its **loop** branch and finishes via the **done** branch once all rows are processed.

![Searching and adding a Loop Over Items node in an n8n workflow](images/Searching and adding a Loop Over Items node in an n8n workflow.png)

### 4. Fetch Active Offers with ScrapeHero

Add the ScrapeHero community node to the **loop** output of the Loop Over Items node.

Search for **ScrapeHero** in the node library and add it to the workflow.

![Searching and adding a ScrapeHero n8n node](images/Searching and adding a ScrapeHero n8n node.png)

To configure your credentials:

1. Go to [app.scrapehero.com](https://app.scrapehero.com/).  
2. Sign in to your account.  
3. Click your profile icon in the upper-right corner.  
4. Open the **API Key** page.  
5. Copy your API key.  
6. Return to n8n and select **Create New Credential**.  
7. Paste your API key into the credential field.  
8. Save the credential.  

![Pasting ScrapeHero Cloud API key](images/Pasting ScrapeHero Cloud API key.png)

In the node parameters:

1. Set **API** to **Amazon Offer Listing**.  
2. In the **ASIN** field, switch to expression mode and enter:

```javascript
={{ $json.ASIN }}
```

Click **Execute Step** to test the request for the first ASIN. ScrapeHero returns product details along with an `offer_listings` array containing all competing seller offers. Pin this output while configuring downstream nodes to prevent redundant API calls during testing.

![Configuring the ScrapeHero n8n node to fetch data from the Amazon Offer Listing API](images/Configuring the ScrapeHero n8n node to fetch data from the Amazon Offer Listing API.png)

## Filter and Count Active FBA Deals

### 5. Split Out the Offer Listings

The `offer_listings` array contains multiple seller objects within a single incoming item. To inspect and count each seller individually, unpack the array into separate items.

Add a **Split Out** node after the ScrapeHero node. In the **Fields To Split Out** parameter, enter:

```javascript
offer_listings
```

Click **Execute Step**. Each seller offer is transformed into its own item containing fields such as `price`, `condition`, `seller`, and `fulfilled_by_amazon`.

![Split Out node unpacking the offer_listings array](images/Split Out node unpacking the offer_listings array.png)

### 6. Filter for Prime-Eligible FBA Offers

To isolate FBA deals from merchant-fulfilled listings, filter the stream by fulfillment type.

Add a **Filter** node after the Split Out node. Set the condition as:

1. **Left Value:** `={{ $json.fulfilled_by_amazon }}`  
2. **Operator:** Boolean `is true`  

Enable **Always Output Data** in the node settings so that if a product currently has zero FBA sellers, an empty item is emitted downstream rather than stalling the execution.

![Configuring the Filter node to keep only FBA offers](images/Configuring the Filter node to keep only FBA offers.png)

### 7. Check for Active FBA Offers

When no FBA offers are present, the Filter node produces an empty object `{}` due to the Always Output Data safeguard. An If node checks whether valid offer data exists before attempting to calculate counts.

Add an **If** node after the Filter node and configure:

1. **Left Value:** `={{ Object.keys($json).length === 0 }}`  
2. **Operator:** Boolean `is false`  

When valid offers exist, this condition evaluates to `true` and routes to the count calculation step. If no FBA offers are present, it evaluates to `false` and routes directly back to the loop.

![Configuring the If node to check for active FBA offers](images/Configuring the If node to check for active FBA offers.png)

### 8. Count Active FBA Offers

To monitor competitive intensity, count how many FBA offers survived the filter for the current product.

Add an **Edit Fields** node to the `true` output of the If node. Add a numeric field named `Count` and assign the expression:

```javascript
={{ $input.all().length }}
```

This expression evaluates the total number of items entering the node simultaneously, capturing the exact count of active FBA sellers for this product.

![Configuring the Edit Fields node to count active FBA offers](images/Configuring the Edit Fields node to count active FBA offers.png)

## Prevent Duplicate Alerts and Record Changes

### 9. Compare Against Previous Counts

Receiving notifications when nothing has changed creates alert fatigue. An If node evaluates whether the newly computed count differs from the baseline stored in your sheet.

Add a second **If** node after the Edit Fields node. Set the condition to:

1. **Left Value:** `={{ $('Loop Over Items').item.json["Previous FBA Count"].toNumber() }}`  
2. **Operator:** Number `not equals`  
3. **Right Value:** `={{ $json.Count }}`  

If the previous count equals the current count, the item routes to `false` and returns to the loop without spamming alerts. If the count has changed, the item routes to `true` for recording and notification.

![Configuring the If node to detect FBA offer count changes](images/Configuring the If node to detect FBA offer count changes.png)

### 10. Append Updated Counts to Google Sheets

When competition shifts, log the updated metric into Google Sheets for historical tracking.

Add a **Google Sheets** node to the `true` output of the second If node. Set **Operation** to **Append Row in Sheet**. Select `FBA Deal Finder` and `Sheet1`.

Under **Columns**, map the fields:

| Column | Expression |
| :--- | :--- |
| **ASIN** | `={{ $('Loop Over Items').item.json.ASIN }}` |
| **Product Name** | `={{ $('Loop Over Items').item.json["Product Name"] }}` |
| **Previous FBA Count** | `={{ $json.Count }}` |

This logs the product's new count, ensuring future runs compare against the updated baseline.

![Configuring the Google Sheets node to append updated FBA counts](images/Configuring the Google Sheets node to append updated FBA counts.png)

### 11. Send Deal Alerts via Google Chat

Simultaneously dispatch an immediate notification to your operations team.

Add a **Google Chat** node to the `true` output of the second If node. Set **Operation** to **Create a Message**, select your alert space, and configure the message text:

```javascript
=FBA Count for {{ $('Loop Over Items').item.json["Product Name"] }} has changed to {{ $json.Count }} from {{ $('Loop Over Items').item.json["Previous FBA Count"] }}
```

Team members receive real-time visibility into seller count spikes or inventory drops.

![Configuring the Google Chat node to send deal alerts](images/Configuring the Google Chat node to send deal alerts.png)

## Test and Complete the Loop

### Connect the Loop

Complete the loop wiring so the execution advances to subsequent ASINs:

1. Connect the output of **Append row in sheet** back to the input of **Loop Over Items**.  
2. Connect the `false` output of **If** back to **Loop Over Items**.  
3. Connect the `false` output of the second If node back to **Loop Over Items**.  

![The complete n8n workflow to monitor Amazon FBA deals using ScrapeHero](images/The complete n8n workflow to monitor Amazon FBA deals using ScrapeHero.png)

### Test the Workflow

1. Unpin any pinned data in the ScrapeHero node.  
2. Click **Execute Workflow** at the bottom of the canvas.  
3. Verify that each ASIN is fetched sequentially.  
4. Confirm that products with changed FBA counts trigger a Google Chat notification and append a row to Google Sheets.  
5. Confirm that products with unchanged counts complete quietly without sending notifications.  

Once verified, click **Publish** to run the workflow automatically on schedule.

## What This Unlocks for Your Business

Implementing automated FBA deals monitoring provides decisive market advantages:

- **Track competitor inventory depletion.** Spot when competing FBA sellers run out of stock, allowing you to capture the Buy Box or increase retail margins.  
- **Eliminate notification fatigue.** Suppress redundant messages by comparing live counts against historical records, ensuring your team acts only on real market shifts.  
- **Protect brand integrity.** Identify unauthorized resellers and liquidators who check unauthorized FBA inventory into Amazon fulfillment centers.  
- **Source profitable arbitrage deals.** Monitor sudden spikes in seller counts to detect clearance dumps and discounted inventory across product categories.  
- **Maintain historical competition records.** Maintain an auditable log of seller fluctuations in Google Sheets to analyze seasonal stock cycles.  

For teams looking for pre-built extractors without maintaining workflow infrastructure, browse ready-to-use options in the [ScrapeHero Marketplace](https://www.scrapehero.com/marketplace/) and review our guide to the [best price monitoring tools](https://www.scrapehero.com/best-price-monitoring-tools/).

## Next Steps

Extend your FBA deals monitoring workflow with these practical enhancements:

- **Multi-channel alerting:** Add Slack, Telegram, or Discord nodes alongside Google Chat to notify distributed sales and procurement channels.  
- **Lowest price threshold logic:** Integrate price-checking expressions within the Edit Fields node to alert only when the lowest FBA price falls below a target profit threshold.  
- **Automated repricing triggers:** Connect webhook outputs to your Amazon repricing engine to automatically adjust list prices when competitor FBA counts change.  
- **Multi-region ASIN tracking:** Add marketplace region identifiers (such as US, UK, DE) to your input sheet to track international FBA competition across borders.  

## Wrapping Up

Automating Amazon FBA deals monitoring with n8n and ScrapeHero transforms manual catalog spot-checks into a reliable, continuous intelligence pipeline. By combining scheduled triggers, API extraction, condition filtering, and state comparison, your operations team stays informed of critical marketplace movements in real time.

The ScrapeHero node handles the complex scraping, proxy management, and anti-bot resolution, returning pristine JSON data directly into your automation canvas.

Sign up for a [ScrapeHero API key](https://app.scrapehero.com/) to build your automated monitoring workflows. If your catalog requires specialized attributes, custom formats, or non-standard frequencies, tell us your requirements and we will build a custom API tailored to your business.

For enterprise brands and retailers monitoring tens of thousands of ASINs across global marketplaces, our fully managed [Amazon scraping services](https://www.scrapehero.com/amazon-scraping-services/) deliver verified, high-volume data straight to your data warehouse or cloud storage. Contact ScrapeHero today to scale your e-commerce data pipeline.

## Frequently Asked Questions

### How do I find the cheapest FBA offers on Amazon?

Use ScrapeHero's Amazon Offer Listing API to pull all active seller offers for a product. Filter the results by setting `fulfilled_by_amazon` to `true`, sort the remaining offers by price ascending, and select the first item to obtain the cheapest FBA offer.

### How do I stop receiving duplicate price and offer alerts in n8n?

Store the previous count or price in your database or Google Sheet. In n8n, use an If node to compare the newly extracted value against the stored baseline. Configure the workflow to dispatch notifications only when the values are not equal, routing unchanged items back into the loop.

### How can I extract Amazon seller and offer details without getting blocked?

Amazon deploys anti-scraping measures against basic HTTP scrapers. Using the ScrapeHero community node in n8n routes requests through ScrapeHero's proxy rotation and browser emulation infrastructure, returning structured JSON without IP blocks or CAPTCHA disruptions.

### How do I connect ScrapeHero's Amazon Offer Listing API to an n8n workflow?

Install the ScrapeHero community node (`n8n-nodes-scrapehero.scrapeHero`) from the n8n community node registry. Add your ScrapeHero API key under credentials, select **Amazon Offer Listing** from the API dropdown, and map the ASIN parameter using an expression such as `={{ $json.ASIN }}`.
