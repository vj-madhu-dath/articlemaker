# How to Track Amazon Keyword Rankings With n8n and ScrapeHero

**SEO title:** n8n Amazon Keyword Rank Tracker [Track Rankings Automatically]

**Meta description:** Build an n8n Amazon keyword rank tracker with ScrapeHero's Amazon Search API and Google Sheets. Pull rankings, compare them to existing records, and update your sheet automatically.

**Category:** ScrapeHero Cloud Resources > n8n

#### Table of contents

- [Before You Begin](#before-you-begin)
- [Create the Workflow](#create-the-workflow)
- [Compare and Update the Rankings](#compare-and-update-the-rankings)
- [Test and Complete the Loop](#test-and-complete-the-loop)
- [What This Unlocks for Your Business](#what-this-unlocks-for-your-business)
- [Next Steps](#next-steps)
- [Wrapping Up](#wrapping-up)
- [Frequently Asked Questions](#frequently-asked-questions)

Tracking Amazon keyword rankings manually takes too much time. Build an n8n Amazon keyword rank tracker to automate the process, and you can see where products rank for the keywords you care about without checking search pages yourself.

This tutorial shows how to build an n8n workflow that:

1. Reads target keywords from Google Sheets
2. Fetches Amazon search results for each keyword through ScrapeHero's Amazon Search API
3. Maps the data, including each product's `rank`, into sheet columns
4. Compares the new results with the existing records, then updates existing rows, adds new products, and deletes outdated listings

### Key Takeaways

- Build an Amazon keyword rank tracker in n8n using ScrapeHero's Amazon Search API.
- Read keywords from Google Sheets and process them one at a time with the Loop Over Items node.
- Use the Split Out node to turn the `search_results` array, which includes the `rank` field, into individual products.
- Use the Merge node to compare new results with existing rows, and update the sheet with Append or Update Row.
- Delete outdated rows from the bottom up to avoid row-shifting bugs in Google Sheets.
- Extend the workflow with rank drop alerts or a separate rank history sheet.

## Before You Begin

Before creating the n8n Amazon keyword rank tracker, prepare the following:

1. An n8n account or self-hosted [n8n installation](https://docs.n8n.io/choose-how-to-use-n8n).
2. A Google [Cloud OAuth client ID and client secret](https://support.google.com/cloud/answer/15549257?hl=en).
3. A Google Sheets document named **Keyword Tracker** with two tabs: **Keywords** and **Rankings**.
4. A [ScrapeHero account and API key.](https://app.scrapehero.com/docs/API-docs/authentication/)

The **Keywords** tab needs one column with the header **Keyword**, with one search term per row:

| Keyword            |
| ------------------ |
| wireless earbuds   |
| robot vacuum       |

The **Rankings** tab holds the results. Add these headers to the first row:

| Keyword | ASIN | Rank | Name | Sale Price | Product URL |
| ------- | ---- | ---- | ---- | ---------- | ----------- |

Scraping Amazon directly from your own IP address leads to CAPTCHAs and rate limits. The ScrapeHero API handles proxy rotation and CAPTCHA solving, so your workflow only deals with structured data.

## Create the Workflow

### 1. Get the Keywords

On your n8n dashboard, click "Create Workflow" to open a new canvas with a big plus sign in the center.

Click the **plus icon**, search for **Google Sheets**, and click to add the node. Rename it to **Get Queries**.

For the Sheet action, choose **Get Row(s) in Sheet**.

Next, click **Connect to Google Sheets**. Paste your Google Cloud **Client ID** and **Client Secret**, then click **Sign in with Google**. Complete the authorization process and return to n8n.

Now select:

1. The **Keyword Tracker** document.
2. The **Keywords** tab.

Click **Execute Step** to confirm that the keywords load.

![Configuring the Google Sheets node to read keywords](add-image-url)

### 2. Process Each Keyword Individually

Each keyword needs its own request to the ScrapeHero API. Processing them one at a time prevents rate limit problems.

To do so, add a **Loop Over Items** node. Click the **plus icon** to the right of the Get Queries node, search for **Loop Over Items**, and click it. Set the **Batch Size** to 1.

![Searching and adding a Loop Over Items node in an n8n workflow](add-image-url)

### 3. Add the ScrapeHero Node

Next, add the ScrapeHero node to the **loop** output of the Loop Over Items node.

If you are adding the node for the first time, you need to install the ScrapeHero community node first.

![Searching and adding a ScrapeHero n8n node](add-image-url)

In the configuration window, click **Connect ScrapeHero** to create the credentials. Then:

1. Go to [app.scrapehero.com](https://app.scrapehero.com/).
2. Sign in to your account.
3. Click your profile icon.
4. Open **API Key**.
5. Copy your API key.
6. Return to n8n.
7. Paste the key into the ScrapeHero credential field.
8. Save the credentials.

![Pasting ScrapeHero Cloud API key](add-image-url)

Select **Amazon Search API** from the API dropdown.

Locate the keyword field and switch to the expression editor, or drag the **Keyword** value from the Loop Over Items node into it. You can also enter the expression directly:

```javascript
{{ $json.Keyword }}
```

Select the Country Code. Use the **Pages** field to fetch deeper results. Each extra page uses more credits, so keep the number small while testing.

Click **Execute Step** to test the request. After the test succeeds, pin the output temporarily so that repeated tests do not make unnecessary API requests.

![Configuring the ScrapeHero n8n node to fetch data from the Amazon Search API](add-image-url)

### 4. Split the Search Results

The API returns a JSON object with a `search_results` array. Each item in the array includes fields such as `asin`, `rank`, `name`, `sale_price`, and `product_url`.

To output each product as its own item, add a **Split Out** node after the ScrapeHero node and rename it to **Prepare New Items**. In the **Fields To Split Out** box, enter:

```
search_results
```

![Adding a Split Out node to separate the search results](add-image-url)

### 5. Format the Data

The API returns field names in `snake_case`. Add an **Edit Fields** node after the Split Out node, and map them to the `Title Case` column names in your sheet.

Add the following fields and drag the matching values from the Split Out output into each one:

| Output Field  | Value                                  |
| ------------- | -------------------------------------- |
| `Keyword`     | The current keyword (see below)        |
| `ASIN`        | `asin`                                 |
| `Rank`        | `rank`                                 |
| `Name`        | `name`                                 |
| `Sale Price`  | `sale_price`                           |
| `Product URL` | `product_url`                          |

For the `Keyword` field, use the following expression. The keyword is needed later to compare each product against the right rows in the sheet.

```javascript
{{ $('Loop Over Items').item.json.Keyword }}
```

![Configuring the Edit Fields node to map the API fields](add-image-url)

## Compare and Update the Rankings

### 6. Get the Existing Listings

To update your sheet without creating duplicates, compare the live data with the data already in the sheet.

Add a **Google Sheets** node after the Edit Fields node, with the action **Get Row(s) in Sheet**. Select the **Keyword Tracker** document and the **Rankings** tab.

Under **Filters**, add a filter on the `Keyword` column and set the value to the current keyword:

```javascript
{{ $('Loop Over Items').item.json.Keyword }}
```

This reads only the existing listings for the keyword being processed. The node also returns a `row_number` for each row, which you need for deletion later.

![Configuring the Google Sheets node to read existing listings for the current keyword](add-image-url)

### 7. Find the Outdated Listings

Add a **Merge** node and rename it to **Find Old Items**. Connect the Edit Fields node (new data) to Input 1 and the Get Existing Listings node to Input 2.

Configure it as follows:

1. Set **Mode** to **Combine**, then **Combine By** to **Matching Fields**.
2. Set the field to match as `ASIN` on both inputs.
3. Set **Output Type** to **Keep Non-Matches**.
4. Set **Output Data From** to **Input 2**.

The node now outputs only the rows that exist in your sheet but no longer appear in the new results. These are the outdated listings. You do not need a Code node to find them.

![Configuring the Merge node to find outdated listings](add-image-url)

### 8. Update the Sheet

Add another **Google Sheets** node after the Edit Fields node and choose **Append or Update Row in Sheet** as the action.

Select the **Keyword Tracker** document and the **Rankings** tab, then set **Mapping Column Mode** to **Map Automatically**. For the matching columns, choose **ASIN** and **Keyword**.

Matching on both columns means the same product can have a separate row for each keyword. Existing rows are updated with the latest rank and price, and new products are added.

![Configuring the Google Sheets node to append or update rankings](add-image-url)

### 9. Delete the Outdated Listings

Now remove the listings that the Merge node identified. Deleting rows from the top down shifts the row numbers in Google Sheets, so rows must be deleted from the bottom up.

Add a **Sort** node after the Merge node. Set the field to `row_number` and the order to **Descending**.

Then add a **Google Sheets** node after the Sort node, choose **Delete Rows or Columns from Sheet** as the action, and select the **Keyword Tracker** document and the **Rankings** tab. Set:

1. **Shift:** Rows
2. **Start Row Number:** `{{ $json.row_number }}`
3. **Number to Delete:** 1

![Configuring the Sort and Delete nodes to remove outdated listings from the bottom up](add-image-url)

## Test and Complete the Loop

### Connect the Loop

Connect the output of the Delete node back to the **Loop Over Items** node. This tells the loop to continue with the next keyword.

If a keyword has no outdated listings, the Merge node outputs nothing and the loop stops early. To prevent this, turn on **Always Output Data** in the Merge node, and add a **Filter** node before the Sort node that keeps only items where `row_number` exists.

![The complete n8n workflow to track Amazon keyword rankings using ScrapeHero](add-image-url)

### Test the Workflow

Unpin all the pinned outputs and click **Execute Workflow** at the bottom of the canvas.

When the run finishes, open the **Rankings** tab. You should see each product with its keyword, ASIN, rank, name, price, and URL. Run the workflow a second time and confirm that existing rows are updated instead of duplicated.

## What This Unlocks for Your Business

Building this workflow to track Amazon keyword rankings with n8n helps you:

- **Monitor rankings without manual checks.** The workflow checks every keyword automatically, so you see ranking changes as soon as they appear in the sheet.
- **Validate SEO changes.** Track rank movements after you update product titles or backend search terms.
- **Analyze share of voice.** See how many placements your brand holds for core keywords compared with competitors.
- **Adjust PPC campaigns.** Use organic ranking positions to decide where to pause or increase bids.
- **Watch competitor prices.** The sale price is stored next to each rank, so you can see how competitors price the products that rank near yours.

Prefer not to handle API integration? Check out the [ScrapeHero Cloud Amazon scrapers](https://www.scrapehero.com/marketplace/) instead.

## Next Steps

You can extend this workflow with:

- **Rank drop alerts**: Add an **If** node after the Merge node or the Edit Fields node. If the rank of a key product moves beyond your chosen position, route the output to a Slack or Gmail node.

- **Rank history**: Instead of updating and deleting rows, append each day's rank to a separate **History** tab with a Google Sheets **Append Row** node. Skip the delete steps.

- **Scheduled runs**: Add a **Schedule Trigger** before the Get Queries node to run the tracker daily.

- **Competitor monitoring**: Use ScrapeHero's Amazon Product Details and Pricing API to track changes in competitor prices and reviews.

## Wrapping Up

Building your own n8n rank tracker gives you full control over your data. You can customize exactly which metrics matter to your Amazon business.

The ScrapeHero API, accessed via the ScrapeHero node, handles the data extraction part. You just have to focus on building the workflow that improves your business.

Sign up for a [ScrapeHero API key](http://app.scrapehero.com) and build your rank tracker. Do you want additional data points? Tell us your requirements, and we will build a custom API just for you.

ScrapeHero is your #1 [web scraping service provider](https://scrapehero.com) for fully outsourcing data extraction. If your data needs grow beyond a DIY workflow, our fully managed [Amazon scraping services](https://www.scrapehero.com/amazon-scraping-services/) can build and maintain custom scrapers and deliver clean, structured data to your preferred databases. Contact ScrapeHero today to get started.

## Frequently Asked Questions

### What should you store if your ASIN isn't in the results?

This workflow stores every product in the search results, so a product that drops out is removed by the delete step. If you want to track specific ASINs over time, log a default "unranked" value, such as 0 or above your page limit, in a separate History tab. That keeps the trend line continuous.

### Should you count sponsored results when tracking Amazon rank?

It depends on what you want to measure. Excluding sponsored results gives you the organic rank. Including them shows the full share of voice and competitor ad activity. Check the API response for a field that marks sponsored listings, then filter on it or store it in its own column.

### How do you handle pagination in n8n for Amazon search results?

Set the **Pages** parameter in the ScrapeHero node to fetch deeper results. You can also build a loop that follows the `next_page` value from the response.
