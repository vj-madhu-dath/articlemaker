#!/usr/bin/env python3
"""
Generates clean, high-resolution template screenshots for common catalog items.
These serve as default reusable images until custom real captures replace them.
"""

import os
import json
from PIL import Image, ImageDraw

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_DIR = os.path.join(ROOT_DIR, "templates", "common_screenshots")
CATALOG_FILE = os.path.join(CATALOG_DIR, "catalog.json")

# Color palette (n8n inspired modern theme)
BG_COLOR = (248, 249, 250)         # Soft canvas light gray
PANEL_BG = (255, 255, 255)         # Pure white panel
BORDER_COLOR = (226, 232, 240)     # Subtle border
HEADER_BG = (241, 245, 249)        # Header gray
TEXT_PRIMARY = (15, 23, 42)        # Slate dark
TEXT_MUTED = (100, 116, 139)       # Slate muted
PRIMARY_COLOR = (255, 109, 90)     # n8n Coral / Orange
ACCENT_GREEN = (34, 197, 94)       # Success green
MARKUP_RED = (255, 34, 0, 255)     # #FF2200 brand red arrow

def create_template_image(title, subtitle, node_name, fields, action_label, arrow_pos="action"):
    width, height = 1200, 680
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Canvas dots grid pattern
    for x in range(20, width, 24):
        for y in range(20, height, 24):
            draw.point((x, y), fill=(210, 215, 225))

    # Modal window shadow & card
    modal_x1, modal_y1, modal_x2, modal_y2 = 180, 80, 1020, 600
    
    # Shadow
    for s in range(8, 0, -1):
        draw.rounded_rectangle(
            [modal_x1 - s, modal_y1 - s, modal_x2 + s, modal_y2 + s],
            radius=12,
            fill=(0, 0, 0, int(12 / s))
        )
    
    # Modal container
    draw.rounded_rectangle([modal_x1, modal_y1, modal_x2, modal_y2], radius=10, fill=PANEL_BG, outline=BORDER_COLOR, width=2)

    # Modal header
    draw.rounded_rectangle([modal_x1, modal_y1, modal_x2, modal_y1 + 64], radius=10, fill=HEADER_BG)
    draw.rectangle([modal_x1, modal_y1 + 50, modal_x2, modal_y1 + 64], fill=HEADER_BG)
    draw.line([(modal_x1, modal_y1 + 64), (modal_x2, modal_y1 + 64)], fill=BORDER_COLOR, width=1)

    # Node icon & title in header
    draw.rounded_rectangle([modal_x1 + 20, modal_y1 + 16, modal_x1 + 52, modal_y1 + 48], radius=6, fill=PRIMARY_COLOR)
    draw.text((modal_x1 + 68, modal_y1 + 16), node_name, fill=TEXT_PRIMARY)
    draw.text((modal_x1 + 68, modal_y1 + 36), subtitle, fill=TEXT_MUTED)

    # Action button (top right of modal)
    btn_x2 = modal_x2 - 24
    btn_x1 = btn_x2 - 130
    btn_y1 = modal_y1 + 16
    btn_y2 = btn_y1 + 34
    draw.rounded_rectangle([btn_x1, btn_y1, btn_x2, btn_y2], radius=6, fill=ACCENT_GREEN)
    draw.text((btn_x1 + 18, btn_y1 + 8), action_label, fill=(255, 255, 255))

    # Form parameters
    cur_y = modal_y1 + 90
    for label, val in fields:
        draw.text((modal_x1 + 40, cur_y), label, fill=TEXT_MUTED)
        cur_y += 20
        # Input field box
        draw.rounded_rectangle([modal_x1 + 40, cur_y, modal_x2 - 40, cur_y + 36], radius=6, fill=(250, 250, 252), outline=BORDER_COLOR, width=1)
        draw.text((modal_x1 + 52, cur_y + 10), val, fill=TEXT_PRIMARY)
        cur_y += 50

    # Draw Red Arrow Markup
    scale = 4
    canvas = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(canvas)

    if arrow_pos == "action":
        tip_x, tip_y = btn_x1 - 10, (btn_y1 + btn_y2) // 2
        direction = "right"
    else:
        tip_x, tip_y = modal_x1 + 400, modal_y1 + 160
        direction = "down"

    tip_xs = tip_x * scale
    tip_ys = tip_y * scale
    head_len = 32 * scale
    head_half_h = 14 * scale
    shaft_half_w = 3 * scale
    total_len = 110 * scale

    if direction == "right":
        start_xs = tip_xs - total_len
        base_xs = tip_xs - head_len
        cdraw.rectangle([start_xs, tip_ys - shaft_half_w, base_xs, tip_ys + shaft_half_w], fill=MARKUP_RED)
        cdraw.polygon([(base_xs, tip_ys - head_half_h), (tip_xs, tip_ys), (base_xs, tip_ys + head_half_h)], fill=MARKUP_RED)
    elif direction == "down":
        start_ys = tip_ys - total_len
        base_ys = tip_ys - head_len
        cdraw.rectangle([tip_xs - shaft_half_w, start_ys, tip_xs + shaft_half_w, base_ys], fill=MARKUP_RED)
        cdraw.polygon([(tip_xs - head_half_h, base_ys), (tip_xs, tip_ys), (tip_xs + head_half_h, base_ys)], fill=MARKUP_RED)

    overlay = canvas.resize((width, height), Image.Resampling.LANCZOS)
    img.alpha_composite(overlay)
    return img

def main():
    os.makedirs(CATALOG_DIR, exist_ok=True)
    with open(CATALOG_FILE, 'r') as f:
        catalog = json.load(f)

    presets = {
        "manual_trigger_add": {
            "title": "Searching and adding Manual Trigger in an n8n workflow",
            "subtitle": "Trigger workflow on demand",
            "node_name": "When clicking ‘Test step’",
            "fields": [
                ("Trigger Type", "Manual Trigger"),
                ("Notes", "Allows testing workflow nodes manually before scheduling")
            ],
            "action": "Add to Canvas",
            "arrow": "action"
        },
        "schedule_trigger_add": {
            "title": "Searching and adding Schedule Trigger in an n8n workflow",
            "subtitle": "Trigger workflow on automated schedule",
            "node_name": "Schedule Trigger",
            "fields": [
                ("Trigger Interval", "Days / Hours"),
                ("Trigger at Hour", "08:00 AM"),
                ("Timezone", "UTC")
            ],
            "action": "Add to Canvas",
            "arrow": "action"
        },
        "loop_items_add": {
            "title": "Searching and adding a Loop Over Items node in an n8n workflow",
            "subtitle": "Split In Batches",
            "node_name": "Loop Over Items",
            "fields": [
                ("Batch Size", "1"),
                ("Mode", "Process each item individually"),
                ("Loop Options", "Reset loop index after completion")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "scrapehero_node_add": {
            "title": "Searching and adding a ScrapeHero n8n node",
            "subtitle": "ScrapeHero Cloud Web Scraper",
            "node_name": "ScrapeHero",
            "fields": [
                ("Community Node", "n8n-nodes-scrapehero.scrapeHero"),
                ("Category", "Web Scraping & Public Web Data"),
                ("Status", "Installed & Ready")
            ],
            "action": "Add Node",
            "arrow": "action"
        },
        "scrapehero_credentials": {
            "title": "Pasting ScrapeHero Cloud API key",
            "subtitle": "ScrapeHero API Credential Configuration",
            "node_name": "ScrapeHero Credentials",
            "fields": [
                ("Credential Name", "ScrapeHero account"),
                ("API Key", "sh_live_••••••••••••••••••••••••••••••••"),
                ("Cloud Endpoint", "https://api.scrapehero.com/v1")
            ],
            "action": "Save Credential",
            "arrow": "action"
        },
        "scrapehero_configure": {
            "title": "Configuring the ScrapeHero n8n node to fetch data",
            "subtitle": "Select API Endpoint and Parameters",
            "node_name": "ScrapeHero Node Configuration",
            "fields": [
                ("API Endpoint", "Amazon Offer Listing / Product Details"),
                ("Query / ASIN Parameter", "={{ $json.asin || $json.query }}"),
                ("Pin Data After Test", "Pin Output for offline testing")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "google_sheets_credentials": {
            "title": "Setting up Google Cloud credentials in an n8n Google Sheets node",
            "subtitle": "Google OAuth2 / Service Account Setup",
            "node_name": "Google Sheets OAuth2",
            "fields": [
                ("Credential Name", "Google Sheets account"),
                ("Authentication", "OAuth2 / Service Account"),
                ("Scopes", "https://www.googleapis.com/auth/spreadsheets")
            ],
            "action": "Sign in with Google",
            "arrow": "action"
        },
        "google_sheets_read": {
            "title": "Configuring the Google Sheets node to read input rows",
            "subtitle": "Google Sheets - Read Operations",
            "node_name": "Get Input Rows",
            "fields": [
                ("Operation", "Get Many Rows"),
                ("Document", "YOUR_GOOGLE_SHEET_DOCUMENT_ID"),
                ("Sheet", "Queries / ASINs")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "google_sheets_create": {
            "title": "Configuring the Google Sheets node with Create Sheet action",
            "subtitle": "Google Sheets - Create Sheet / Tab",
            "node_name": "Create Sheet",
            "fields": [
                ("Operation", "Create New Sheet / Tab"),
                ("Document", "YOUR_GOOGLE_SHEET_DOCUMENT_ID"),
                ("Title", "Daily Deals / Results")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "google_sheets_update": {
            "title": "Configuring the Google Sheets node to update data",
            "subtitle": "Google Sheets - Append / Update Operations",
            "node_name": "Update Sheets",
            "fields": [
                ("Operation", "Append or Update (Upsert)"),
                ("Document", "YOUR_GOOGLE_SHEET_DOCUMENT_ID"),
                ("Matching Column", "asin / id")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "split_out_node": {
            "title": "Split Out node unpacking the items array",
            "subtitle": "Item Lists / Data Transformation",
            "node_name": "Split Out",
            "fields": [
                ("Operation", "Split Out Items Into Separate Rows"),
                ("Field to Split Out", "search_results / offer_listings"),
                ("Include Other Fields", "True")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "filter_node": {
            "title": "Configuring the Filter node",
            "subtitle": "Filter Items by Condition",
            "node_name": "Filter Node",
            "fields": [
                ("Condition Type", "String is equal to"),
                ("Field", "={{ $json.condition }}"),
                ("Expected Value", "New")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "edit_fields_node": {
            "title": "Configuring the Edit Fields node",
            "subtitle": "Transform and Map Values",
            "node_name": "Edit Fields (Set)",
            "fields": [
                ("Field Assignment", "price_num = {{ Number($json.price.replace(/[^0-9.]/g, '')) }}"),
                ("Keep Only Set Fields", "False")
            ],
            "action": "Execute Step",
            "arrow": "action"
        },
        "sort_node": {
            "title": "Configuring the Sort node to order items",
            "subtitle": "Sort List of Items",
            "node_name": "Sort",
            "fields": [
                ("Field Name", "price_num"),
                ("Order", "Ascending (Lowest first)")
            ],
            "action": "Execute Step",
            "arrow": "action"
        }
    }

    for entry in catalog.get("entries", []):
        key = entry["key"]
        filename = entry["filename"]
        out_path = os.path.join(CATALOG_DIR, filename)
        if key in presets:
            p = presets[key]
            img = create_template_image(
                title=p["title"],
                subtitle=p["subtitle"],
                node_name=p["node_name"],
                fields=p["fields"],
                action_label=p["action"],
                arrow_pos=p["arrow"]
            )
            img.save(out_path)
            print(f"✅ Generated common screenshot: {filename}")

if __name__ == "__main__":
    main()
