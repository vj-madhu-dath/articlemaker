#!/usr/bin/env python3
"""
Automated n8n Browser Screenshot Generator with Dark Mode & ScrapeHero Standard Markups.
Controls Chrome via Playwright using the authenticated profile at 1920x1080.
Uses dynamic DOM bounding boxes to guarantee 100% pixel-perfect alignment:
- Arrows point directly at target items with an exact 10px margin (no floating space).
- Rectangles enclose full parameter labels and input containers with 8px clearance (no text slicing).
"""

import os
import sys
import re
import json
import time
import shutil
import argparse
from typing import Optional, Dict, List
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(ROOT_DIR, ".n8n_browser_profile")
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")

sys.path.insert(0, os.path.join(ROOT_DIR, "utils"))
import screenshot_manager
import markup_helper

WORKFLOW_MAP = {
    "amazon-offer-listing-lowest-price": "haNJWsM76BdVtGJX",
    "amazon-product-discount-tracker": "IWU2MRiCcBqRkVGH"
}

def get_workflow_id(article_dir: str) -> Optional[str]:
    slug = os.path.basename(os.path.abspath(article_dir))
    if slug in WORKFLOW_MAP:
        return WORKFLOW_MAP[slug]
    wf_file = os.path.join(article_dir, "workflow.json")
    if os.path.exists(wf_file):
        try:
            with open(wf_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "id" in data:
                return data["id"]
        except Exception:
            pass
    return None

def extract_node_name(el) -> str:
    """Extracts node name from canvas node element, ignoring badge tokens."""
    full_text = el.inner_text().strip()
    ignore_tokens = {'done', 'loop', 'kept', '1 item', '4 items', '2 items', 'execute workflow', 'manual'}
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    valid_lines = [l for l in lines if l.lower() not in ignore_tokens and not l.startswith('read:') and not l.startswith('appendOrUpdate:') and not l.startswith('amazon')]
    if valid_lines:
        return valid_lines[0]
    return lines[0] if lines else "Node"

def capture_side_panel_search(page, query: str, out_path: str):
    """Opens node creator panel, searches for query, and dynamically marks the result card."""
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    
    got_it = page.locator('button:has-text("Got it")')
    if got_it.count() > 0:
        got_it.click()
        page.wait_for_timeout(300)
        
    page.keyboard.press("n")
    page.wait_for_timeout(1000)
    
    search_input = page.locator('input[placeholder*="Search"], [data-test-id="node-creator-search"]').first
    if search_input.count() > 0 and search_input.is_visible():
        search_input.fill(query)
        page.wait_for_timeout(1000)
        
        # Take full 1920x1080 screenshot
        page.screenshot(path=out_path)
        
        # Dynamically locate the search item row to align arrow with 10px margin
        item_row = page.locator(f'[class*="item"]:has-text("{query}"), [class*="node-creator-item"]:has-text("{query}")').first
        if item_row.count() == 0 or not item_row.is_visible():
            # Fallback to first item in side panel list
            item_row = page.locator('[class*="item-list"] > div, [class*="list-item"]').first
            
        if item_row.count() > 0 and item_row.is_visible():
            b = item_row.bounding_box()
            if b:
                tip_x = int(b['x'] - 10)
                tip_y = int(b['y'] + b['height'] / 2)
                markup_helper.draw_arrow(out_path, tip_x=tip_x, tip_y=tip_y, direction='right', length=120, out_path=out_path)
                print(f"   🎯 Dynamically aligned arrow on '{query}' at ({tip_x}, {tip_y})")
        else:
            # Fallback based on verified 1920x1080 side panel coordinates
            markup_helper.draw_arrow(out_path, tip_x=1525, tip_y=220, direction='right', length=120, out_path=out_path)
            
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        return True
    return False

def get_param_group_box(page, param_keywords: List[str]) -> Optional[tuple]:
    """
    Dynamically inspects the live DOM inside NDV to compute the exact bounding box
    (x1, y1, x2, y2) encompassing the requested parameter labels and input containers.
    """
    boxes = []
    # If filter condition
    if any('condition' in k.lower() for k in param_keywords):
        cond = page.locator('[class*="condition"]').first
        if cond.count() > 0 and cond.is_visible():
            b = cond.bounding_box()
            if b and b['width'] > 200:
                boxes.append(b)
                
    if not boxes:
        items = page.locator('[class*="parameter-item"], [class*="parameterItem"]').all()
        for it in items:
            if not it.is_visible():
                continue
            txt = it.inner_text().lower()
            if any(k.lower() in txt for k in param_keywords):
                b = it.bounding_box()
                if b and b['width'] > 50 and b['height'] > 10 and b['x'] >= 700:
                    boxes.append(b)
                    
    if not boxes:
        return None
        
    pad = 8
    min_x = min(b['x'] for b in boxes) - pad
    min_y = min(b['y'] for b in boxes) - pad
    max_x = max(b['x'] + b['width'] for b in boxes) + pad
    max_y = max(b['y'] + b['height'] for b in boxes) + pad
    return (int(min_x), int(min_y), int(max_x), int(max_y))

def get_image_execute_map(article_path: str) -> Dict[str, bool]:
    """
    Parses article.md to determine which image/step explicitly mentions clicking Execute Step.
    Returns a dictionary mapping sanitized filename and alt text to a boolean.
    """
    if not os.path.exists(article_path):
        return {}
        
    with open(article_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = content.split('\n')
    current_section = []
    image_exec_map = {}
    
    def process_section(sec_lines):
        text = '\n'.join(sec_lines)
        has_exec = bool(re.search(r'\b(?:execute\s+step|test\s+(?:the\s+)?step|click\s+(?:\*\*)?execute\s+step\b)', text, re.IGNORECASE))
        imgs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', text)
        for alt, src in imgs:
            fn = os.path.basename(src)
            image_exec_map[fn] = has_exec
            image_exec_map[alt.lower()] = has_exec

    for line in lines:
        if line.startswith('## ') or line.startswith('### '):
            if current_section:
                process_section(current_section)
            current_section = [line]
        else:
            current_section.append(line)
    if current_section:
        process_section(current_section)
        
    return image_exec_map

def apply_ndv_markup(node_name: str, shot_path: str, page, show_execute_arrow: bool = False):
    """Dynamically applies bounding boxes and action arrows using live DOM element metrics."""
    nl = node_name.lower()
    
    # 1. Dynamic Parameter Bounding Box
    box = None
    if "asin" in nl or "read" in nl or "keyword" in nl:
        box = get_param_group_box(page, ['Document', 'Sheet'])
    elif "create sheet" in nl:
        box = get_param_group_box(page, ['Document', 'Title'])
    elif "loop" in nl:
        box = get_param_group_box(page, ['Batch Size'])
    elif "scrapehero" in nl:
        box = get_param_group_box(page, ['API', 'ASIN', 'Country Code', 'Keyword'])
    elif "split out" in nl:
        box = get_param_group_box(page, ['Fields To Split Out'])
    elif "filter" in nl or "kept" in nl:
        box = get_param_group_box(page, ['condition'])
    elif "edit fields" in nl:
        box = get_param_group_box(page, ['Fields to Set'])
    elif "sort" in nl:
        box = get_param_group_box(page, ['Type', 'Order'])
    elif "update" in nl or "save deals" in nl or "append" in nl:
        box = get_param_group_box(page, ['Document', 'Sheet', 'Mapping Column Mode', 'Lowest New Price'])

    if box:
        markup_helper.draw_box(shot_path, x1=box[0], y1=box[1], x2=box[2], y2=box[3], stroke_width=6)
        print(f"   📦 Applied dynamic parameter box: {box}")

    # 2. Horizontal Arrow on Execute step button (only if explicitly mentioned in the article step)
    if show_execute_arrow:
        exec_btn = page.locator('button:has-text("Execute step"), button:has-text("Test step")').first
        if exec_btn.count() > 0 and exec_btn.is_visible():
            btn_box = exec_btn.bounding_box()
            if btn_box:
                tip_x = int(btn_box['x'] - 10)
                tip_y = int(btn_box['y'] + btn_box['height'] / 2)
                markup_helper.draw_arrow(shot_path, tip_x=tip_x, tip_y=tip_y, direction="right", length=110, out_path=shot_path)
                print(f"   🎯 Applied arrow to Execute step button at ({tip_x}, {tip_y})")

    # 3. Diagonal Arrow on Pin Data icon (only if pinned banner or pin icon is visible)
    pinned_banner = page.locator('text="This data is pinned"').first
    pin_btn = page.locator('button:has([class*="pin"]), [aria-label*="pin" i]').first
    if pinned_banner.count() > 0 and pinned_banner.is_visible() and pin_btn.count() > 0 and pin_btn.is_visible():
        pin_box = pin_btn.bounding_box()
        if pin_box:
            tip_x = int(pin_box['x'] + pin_box['width'] / 2)
            tip_y = int(pin_box['y'] + pin_box['height'] / 2)
            markup_helper.draw_arrow(shot_path, tip_x=tip_x, tip_y=tip_y, direction="up-right", length=90, out_path=shot_path)

def auto_capture_article(article_dir: str, workflow_id: Optional[str] = None, theme: str = "dark"):
    article_path = screenshot_manager.find_article_file(article_dir)
    images_dir = os.path.join(os.path.dirname(article_path), "images")
    os.makedirs(images_dir, exist_ok=True)

    if not workflow_id:
        workflow_id = get_workflow_id(article_dir)

    if not workflow_id:
        print(f"Error: Could not determine workflow ID for {article_dir}.")
        return False

    wf_url = f"{N8N_BASE_URL}/workflow/{workflow_id}"
    print(f"\n🚀 Automating live 1920x1080 browser capture for: {os.path.basename(article_dir)} [Theme: {theme.upper()}]")
    print(f"🔗 Target: {wf_url}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            executable_path=CHROME_BIN if os.path.exists(CHROME_BIN) else None,
            headless=True,
            color_scheme=theme,
            viewport={"width": 1920, "height": 1080},
            args=["--no-sandbox"]
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(wf_url, wait_until="networkidle")
        page.wait_for_timeout(3500)

        if "/signin" in page.url:
            print("❌ Authentication failed. Please log in first.")
            context.close()
            return False

        # Fit canvas view
        page.keyboard.press("1")
        page.wait_for_timeout(1000)

        items = screenshot_manager.parse_article_images(article_path)
        image_exec_map = get_image_execute_map(article_path)

        # 1. Capture Overview / Complete Workflow Canvas (clean, no markup)
        for it in items:
            alt = it["alt_text"]
            if it["is_workflow_overview"] or "complete n8n workflow" in alt.lower():
                fn = screenshot_manager.sanitize_filename(alt)
                fp = os.path.join(images_dir, fn)
                page.screenshot(path=fp)
                print(f"📸 Captured Complete Workflow Canvas (clean): images/{fn}")

        # 2. Capture Side Panel Search Steps ("Searching and adding ...")
        for it in items:
            alt = it["alt_text"]
            alt_l = alt.lower()
            if "searching and adding" in alt_l or "adding a split out node" in alt_l:
                query = None
                if "manual trigger" in alt_l:
                    query = "Manual Trigger"
                elif "schedule trigger" in alt_l:
                    query = "Schedule Trigger"
                elif "loop over items" in alt_l:
                    query = "Loop Over Items"
                elif "scrapehero" in alt_l:
                    query = "ScrapeHero"
                elif "split out" in alt_l:
                    query = "Split Out"
                elif "filter" in alt_l:
                    query = "Filter"
                elif "edit fields" in alt_l:
                    query = "Edit Fields"
                elif "sort" in alt_l:
                    query = "Sort"

                if query:
                    fn = screenshot_manager.sanitize_filename(alt)
                    fp = os.path.join(images_dir, fn)
                    capture_side_panel_search(page, query, fp)

        # 3. Capture Credential Modal ("Pasting ScrapeHero Cloud API key")
        cred_items = [it for it in items if "pasting scrapehero" in it["alt_text"].lower() or "cloud api key" in it["alt_text"].lower()]
        if cred_items:
            nodes = page.locator('[data-test-id="canvas-node"]').all()
            for n in nodes:
                if "scrapehero" in n.inner_text().lower():
                    n.dblclick()
                    page.wait_for_timeout(1500)
                    edit_btn = page.locator('[data-test-id="credential-edit-button"]').first
                    if edit_btn.count() > 0:
                        edit_btn.click()
                        page.wait_for_timeout(1500)

                        key_input = page.locator('input[type="password"], input[name*="apiKey"]').first
                        kbox = key_input.bounding_box() if key_input.count() > 0 and key_input.is_visible() else None

                        for cit in cred_items:
                            fn = screenshot_manager.sanitize_filename(cit["alt_text"])
                            fp = os.path.join(images_dir, fn)
                            page.screenshot(path=fp)
                            if kbox:
                                markup_helper.draw_box(fp, x1=int(kbox['x'] - 8), y1=int(kbox['y'] - 8),
                                                       x2=int(kbox['x'] + kbox['width'] + 8), y2=int(kbox['y'] + kbox['height'] + 8), stroke_width=6)
                            print(f"📸 Captured Credential Modal with dynamic box: images/{fn}")
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(500)
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                    break

        # 4. Iterate over canvas nodes and capture NDVs
        nodes = page.locator('[data-test-id="canvas-node"]').all()
        print(f"\n📍 Capturing NDVs for {len(nodes)} canvas nodes...")
        for idx, el in enumerate(nodes, 1):
            try:
                node_name = extract_node_name(el)
                print(f"👉 [{idx}/{len(nodes)}] Opening NDV: '{node_name}'...")
                el.dblclick()
                page.wait_for_timeout(1500)

                ndv = page.locator('[data-test-id="ndv"]')
                if ndv.count() > 0 and ndv.first.is_visible():
                    matched_items = []
                    for it in items:
                        alt = it["alt_text"]
                        alt_l = alt.lower()
                        if it["is_workflow_overview"] or "searching and adding" in alt_l or "pasting scrapehero" in alt_l:
                            continue
                        if "asin" in node_name.lower() and "asin" in alt_l:
                            matched_items.append(it)
                        elif "create sheet" in node_name.lower() and "create sheet" in alt_l:
                            matched_items.append(it)
                        elif "keyword" in node_name.lower() and "keyword" in alt_l:
                            matched_items.append(it)
                        elif "loop" in node_name.lower() and ("loop" in alt_l and "configuring" in alt_l):
                            matched_items.append(it)
                        elif "scrapehero" in node_name.lower() and ("scrapehero" in alt_l and "configuring" in alt_l):
                            matched_items.append(it)
                        elif "split out" in node_name.lower() and ("split out" in alt_l and ("unpacking" in alt_l or "configuring" in alt_l or "separate" in alt_l)):
                            matched_items.append(it)
                        elif ("filter" in node_name.lower() or "kept" in node_name.lower()) and "filter" in alt_l:
                            matched_items.append(it)
                        elif "edit fields" in node_name.lower() and "edit fields" in alt_l:
                            matched_items.append(it)
                        elif "sort" in node_name.lower() and "sort" in alt_l:
                            matched_items.append(it)
                        elif "update" in node_name.lower() and ("update" in alt_l or "lowest price" in alt_l):
                            matched_items.append(it)
                        elif "save deals" in node_name.lower() and ("append" in alt_l or "dated tab" in alt_l):
                            matched_items.append(it)

                    for mit in matched_items:
                        fn = screenshot_manager.sanitize_filename(mit["alt_text"])
                        fp = os.path.join(images_dir, fn)
                        page.screenshot(path=fp)
                        show_exec = image_exec_map.get(fn, False) or image_exec_map.get(mit["alt_text"].lower(), False)
                        apply_ndv_markup(node_name, fp, page, show_execute_arrow=show_exec)
                        print(f"   ✅ Saved full NDV snapshot (execute_arrow={show_exec}): images/{fn}")

                page.keyboard.press("Escape")
                page.wait_for_timeout(700)
            except Exception as e:
                print(f"   ⚠️ Could not capture NDV {idx}: {e}")
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)

        context.close()

    print(f"\n🎉 Live browser automation complete for: {os.path.basename(article_dir)}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Automate n8n screenshots via browser.")
    parser.add_argument("article", help="Article directory or slug")
    parser.add_argument("--workflow-id", default=None, help="Explicit n8n workflow ID")
    parser.add_argument("--theme", default="dark", choices=["dark", "light"], help="UI theme (default: dark)")
    args = parser.parse_args()

    article_dir = args.article
    if not os.path.exists(article_dir):
        cand = os.path.join(ROOT_DIR, "articles", article_dir)
        if os.path.exists(cand):
            article_dir = cand

    auto_capture_article(article_dir, args.workflow_id, args.theme)

if __name__ == "__main__":
    main()
