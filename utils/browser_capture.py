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
AUTH_STATE_PATH = os.path.join(PROFILE_DIR, "auth_state.json")
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")

sys.path.insert(0, os.path.join(ROOT_DIR, "utils"))
import screenshot_manager
import markup_helper

WORKFLOW_MAP = {
    "amazon-offer-listing-lowest-price": "haNJWsM76BdVtGJX",
    "amazon-product-discount-tracker": "IWU2MRiCcBqRkVGH",
    "amazon-fba-deal-finder": "87pzTj4j27pnXosR",
    "FBA Deal Finder": "87pzTj4j27pnXosR"
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
    ignore_tokens = {'done', 'loop', 'kept', 'success', 'error', 'waiting', 'running', 'failed', 'canceled', 'cancelled', 'skipped', '1 item', '4 items', '2 items', '0 items', 'execute workflow', 'manual', 'true', 'false', '1', '2'}
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    valid_lines = [l for l in lines if l.lower() not in ignore_tokens and not l.startswith('read:') and not l.startswith('appendOrUpdate:') and not l.startswith('append:') and not l.startswith('amazon') and not l.startswith('create:')]
    if valid_lines:
        return valid_lines[0]
    return lines[0] if lines else "Node"

def dismiss_overlays(page):
    """Closes any open panel or onboarding popover."""
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    got_it = page.locator('button:has-text("Got it")')
    if got_it.count() > 0:
        try:
            got_it.click()
            page.wait_for_timeout(250)
        except Exception:
            pass


def node_creator_open(page) -> bool:
    search_input = page.locator('input[placeholder*="Search"], [data-test-id="node-creator-search"]').first
    return search_input.count() > 0 and search_input.is_visible()


def find_canvas_node(page, node_name: str):
    """Finds a canvas node element by its visible name."""
    nodes = page.locator('[data-test-id="canvas-node"]').all()
    for el in nodes:
        try:
            if extract_node_name(el) == node_name:
                return el
        except Exception:
            continue
    for el in nodes:
        try:
            if extract_node_name(el).lower() == node_name.lower():
                return el
        except Exception:
            continue
    return None


def open_node_creator(page, parent_name: Optional[str] = None, output_index: int = 0) -> bool:
    """Opens the node creator panel, preferring the plus handle on the parent output."""
    dismiss_overlays(page)

    if parent_name:
        node = find_canvas_node(page, parent_name)
        if node:
            try:
                node.hover()
                page.wait_for_timeout(400)
                node_box = node.bounding_box()

                plus_buttons = []
                seen = set()
                candidates = list(node.locator('[data-test-id="canvas-handle-plus"]').all())
                if node_box:
                    candidates += page.locator('[data-test-id="canvas-handle-plus"]').all()
                for el in candidates:
                    try:
                        b = el.bounding_box()
                        if not b or not el.is_visible():
                            continue
                        key = (round(b['x']), round(b['y']))
                        if key in seen:
                            continue
                        if node_box and b['x'] < node_box['x'] + node_box['width'] - 8:
                            continue
                        if node_box and b['x'] > node_box['x'] + node_box['width'] + 220:
                            continue
                        if node_box and not (node_box['y'] - 20 <= b['y'] <= node_box['y'] + node_box['height'] + 20):
                            continue
                        seen.add(key)
                        plus_buttons.append((b['y'], el))
                    except Exception:
                        continue

                plus_buttons.sort(key=lambda item: item[0])
                if plus_buttons:
                    idx = min(max(output_index, 0), len(plus_buttons) - 1)
                    plus_buttons[idx][1].click()
                    page.wait_for_timeout(900)
                    if node_creator_open(page):
                        return True
            except Exception as e:
                print(f"   ⚠️ Plus-handle open failed for '{parent_name}': {e}")

    # Empty-canvas flow: click the "Add first step" trigger tile.
    if not parent_name:
        for selector in (
            '[data-test-id="canvas-add-first-step"]',
            'button:has-text("Add first step")',
            'div:has-text("Add first step")',
        ):
            candidate = page.locator(selector).first
            if candidate.count() > 0 and candidate.is_visible():
                try:
                    candidate.click()
                    page.wait_for_timeout(900)
                    if node_creator_open(page):
                        return True
                except Exception:
                    continue

    page.keyboard.press("n")
    page.wait_for_timeout(1000)
    if node_creator_open(page):
        return True

    # Last-resort empty-canvas fallback.
    if parent_name:
        for selector in (
            '[data-test-id="canvas-add-first-step"]',
            'button:has-text("Add first step")',
            'div:has-text("Add first step")',
        ):
            candidate = page.locator(selector).first
            if candidate.count() > 0 and candidate.is_visible():
                try:
                    candidate.click()
                    page.wait_for_timeout(900)
                    if node_creator_open(page):
                        return True
                except Exception:
                    continue

    return False


def find_result_card(page, query: str):
    """Locates the node creator result card for the searched node."""
    cards = page.locator('[class*="creatorNode"]').all()
    if not cards:
        cards = page.locator('[class*="nodeItem"]').all()

    for el in cards:
        try:
            if not el.is_visible():
                continue
            first_line = el.inner_text().strip().split('\n')[0].strip()
            if first_line.lower().startswith(query.lower()):
                return el
        except Exception:
            continue

    for selector in (
        f'[class*="creatorNode"]:has-text("{query}")',
        f'[class*="nodeItem"]:has-text("{query}")',
        f'[class*="node-creator-item"]:has-text("{query}")',
        f'[class*="item"]:has-text("{query}")',
        '[class*="item-list"] > div, [class*="list-item"]',
    ):
        candidate = page.locator(selector).first
        if candidate.count() > 0 and candidate.is_visible():
            return candidate
    return None


def find_card_by_name(page, name: str):
    """Finds a node creator card whose title exactly matches the given name."""
    cards = page.locator('[class*="creatorNode"]').all()
    if not cards:
        cards = page.locator('[class*="nodeItem"]').all()

    target = name.strip().lower()
    for el in cards:
        try:
            if not el.is_visible():
                continue
            first_line = el.inner_text().strip().split('\n')[0].strip().lower()
            if first_line == target:
                return el
        except Exception:
            continue
    return None


def is_app_category_card(card) -> bool:
    """True when the card drills into an app's action list instead of adding a node."""
    try:
        return card.locator('button:has(svg[data-icon="arrow-right"])').count() > 0
    except Exception:
        return False


def capture_search_result(page, query: str, out_path: str, action: Optional[str] = None) -> bool:
    """Searches inside an already-open node creator and screenshots the result card.

    When ``action`` is provided (for app nodes such as Google Sheets), drill into
    the app card and point the arrow at the specific action the reader needs.
    """
    search_input = page.locator('input[placeholder*="Search"], [data-test-id="node-creator-search"]').first
    if search_input.count() == 0 or not search_input.is_visible():
        return False

    search_input.fill(query)
    page.wait_for_timeout(1000)

    highlighted = find_result_card(page, query)
    highlighted_label = query

    if action:
        action_card = find_card_by_name(page, action)
        if action_card is None and highlighted is not None and is_app_category_card(highlighted):
            highlighted.click()
            page.wait_for_timeout(1000)
            action_card = find_card_by_name(page, action)
        if action_card is not None:
            highlighted = action_card
            highlighted_label = action

    page.screenshot(path=out_path)

    if highlighted is not None:
        b = highlighted.bounding_box()
        if b:
            tip_x = int(b['x'] - 10)
            tip_y = int(b['y'] + b['height'] / 2)
            markup_helper.draw_arrow(out_path, tip_x=tip_x, tip_y=tip_y, direction='right', length=120, out_path=out_path)
            print(f"   🎯 Dynamically aligned arrow on '{highlighted_label}' at ({tip_x}, {tip_y})")
    else:
        # Fallback based on verified 1920x1080 side panel coordinates
        markup_helper.draw_arrow(out_path, tip_x=1525, tip_y=220, direction='right', length=120, out_path=out_path)

    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    return True


def capture_side_panel_search(page, query: str, out_path: str):
    """Opens node creator panel, searches for query, and dynamically marks the result card."""
    if not open_node_creator(page):
        return False
    return capture_search_result(page, query, out_path)


# ---------------------------------------------------------------------------
# Progressive ("building one node at a time") capture
# ---------------------------------------------------------------------------

CAPTURE_PLAN_FILE = "capture_plan.json"


def load_capture_plan(article_dir: str) -> Optional[dict]:
    plan_path = os.path.join(article_dir, CAPTURE_PLAN_FILE)
    if not os.path.exists(plan_path):
        return None
    with open(plan_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _rest_call(page, method: str, path: str, payload=None) -> dict:
    """Calls n8n's internal REST API with the authenticated browser session."""
    browser_id = page.evaluate("() => localStorage.getItem('n8n-browserId') || localStorage.getItem('browserId') || ''")
    headers = {"Accept": "application/json"}
    if browser_id:
        headers["browser-id"] = browser_id
    kwargs = {"method": method, "headers": headers}
    if payload is not None:
        headers["Content-Type"] = "application/json"
        kwargs["data"] = json.dumps(payload)

    response = page.context.request.fetch(f"{N8N_BASE_URL}{path}", **kwargs)
    text = response.text()
    try:
        data = json.loads(text)
    except Exception:
        data = {"raw": text}
    return {"ok": response.ok, "status": response.status, "data": data}


def rest_get_workflow(page, workflow_id: str) -> dict:
    result = _rest_call(page, "GET", f"/rest/workflows/{workflow_id}")
    if not result.get("ok"):
        raise RuntimeError(f"Could not fetch workflow {workflow_id}: HTTP {result.get('status')}")
    data = result.get("data") or {}
    return data.get("data", data)


def rest_create_workflow(page, payload: dict) -> str:
    result = _rest_call(page, "POST", "/rest/workflows", payload)
    if not result.get("ok"):
        raise RuntimeError(f"Could not create staging workflow: HTTP {result.get('status')} {str(result.get('data'))[:300]}")
    data = result.get("data") or {}
    workflow = data.get("data", data)
    workflow_id = workflow.get("id")
    if not workflow_id:
        raise RuntimeError(f"Staging workflow response did not include an id: {str(data)[:300]}")
    return workflow_id


def rest_archive_workflow(page, workflow_id: str):
    """Archives a workflow. n8n 2.x requires this before a workflow can be deleted."""
    result = _rest_call(page, "POST", f"/rest/workflows/{workflow_id}/archive", {})
    if not result.get("ok"):
        raise RuntimeError(f"Could not archive staging workflow {workflow_id}: HTTP {result.get('status')} {str(result.get('data'))[:200]}")


def rest_delete_workflow(page, workflow_id: str):
    archive_error = None
    try:
        rest_archive_workflow(page, workflow_id)
    except Exception as e:
        archive_error = e

    result = _rest_call(page, "DELETE", f"/rest/workflows/{workflow_id}")
    if not result.get("ok"):
        detail = str(result.get('data'))[:200]
        if archive_error:
            raise RuntimeError(f"Could not delete staging workflow {workflow_id}: HTTP {result.get('status')} {detail}; archive failed: {archive_error}")
        raise RuntimeError(f"Could not delete staging workflow {workflow_id}: HTTP {result.get('status')} {detail}")


def build_stage_payload(live_workflow: dict, plan: dict, built_count: int) -> dict:
    """
    Builds the canvas state before the current stage: only nodes the reader has
    already added. Connections are kept only when both endpoints exist and the
    target comes later, so loop-back wiring appears only after the wiring section.
    """
    stages = plan.get("stages", [])
    names = [stage["node"] for stage in stages[:max(0, built_count)]]
    order = {name: idx for idx, name in enumerate(names)}

    nodes = [dict(node) for node in live_workflow.get("nodes", []) if node.get("name") in order]
    nodes.sort(key=lambda node: order.get(node.get("name"), 999))

    connections = {}
    for source, connection in (live_workflow.get("connections") or {}).items():
        if source not in order:
            continue
        kept_connection = {}
        for connection_type, branches in connection.items():
            kept_branches = []
            for branch in branches:
                kept_branches.append([
                    target for target in branch
                    if target.get("node") in order and order[target["node"]] > order[source]
                ])
            kept_connection[connection_type] = kept_branches
        if any(any(branch) for branch in kept_connection.values()):
            connections[source] = kept_connection

    payload = {
        "name": plan.get("workflow_name") or live_workflow.get("name", "Workflow"),
        "nodes": nodes,
        "connections": connections,
        "settings": live_workflow.get("settings") or {},
        "active": False,
        "meta": {"stagingCapture": True},
    }

    pin_data = {
        name: value for name, value in (live_workflow.get("pinData") or {}).items()
        if name in order
    }
    if pin_data:
        payload["pinData"] = pin_data

    return payload


def reset_zoom_to_100(page):
    """Restores the canvas to 100% zoom so partial stages match the final screenshots."""
    for selector in (
        '[data-test-id="zoom-reset"]',
        '[data-test-id="reset-zoom"]',
        'button[title*="Reset zoom" i]',
        'button[aria-label*="Reset zoom" i]',
    ):
        button = page.locator(selector).first
        if button.count() > 0 and button.is_visible():
            try:
                button.click()
                page.wait_for_timeout(500)
                return
            except Exception:
                continue


def click_zoom_button(page, direction: str) -> bool:
    for selector in (
        f'[data-test-id="zoom-{direction}-button"]',
        f'[data-test-id="zoom-{direction}"]',
        f'button[title*="Zoom {direction}" i]',
        f'button[aria-label*="Zoom {direction}" i]',
    ):
        button = page.locator(selector).first
        if button.count() > 0 and button.is_visible():
            try:
                button.click()
                page.wait_for_timeout(250)
                return True
            except Exception:
                continue
    return False


def ensure_100_percent_zoom(page):
    """Normalizes the canvas to roughly 100% zoom using node card width as the signal."""
    for _ in range(10):
        node = page.locator('[data-test-id="canvas-node"]').first
        if node.count() == 0:
            return
        box = node.bounding_box()
        if not box:
            return
        width = box['width']
        if 165 <= width <= 235:
            return
        if width > 235:
            if not click_zoom_button(page, "out"):
                page.mouse.click(273, 1008)
        else:
            if not click_zoom_button(page, "in"):
                page.mouse.click(305, 1008)
        page.wait_for_timeout(300)


def find_empty_canvas_point(page):
    """Finds a spot on the canvas that is not covered by a node, for panning."""
    boxes = []
    for el in page.locator('[data-test-id="canvas-node"]').all():
        try:
            box = el.bounding_box()
            if box:
                boxes.append(box)
        except Exception:
            continue

    def is_empty(x, y):
        for box in boxes:
            if (box['x'] - 16 <= x <= box['x'] + box['width'] + 16 and
                    box['y'] - 16 <= y <= box['y'] + box['height'] + 16):
                return False
        try:
            over_node = page.evaluate(
                "([x, y]) => { const el = document.elementFromPoint(x, y); return !!(el && el.closest('[data-test-id=\"canvas-node\"]')); }",
                [x, y],
            )
        except Exception:
            over_node = False
        return not over_node

    for x, y in (
        (300, 200), (300, 900), (1450, 900), (800, 900), (300, 500),
        (1400, 200), (800, 150), (500, 700), (1200, 500), (1000, 900),
        (1450, 300), (400, 350),
    ):
        if is_empty(x, y):
            return x, y
    return 300, 200


def pan_canvas(page, dx: int, dy: int):
    """Pans the canvas using a middle-button drag on empty space."""
    start_x, start_y = find_empty_canvas_point(page)
    page.mouse.move(start_x, start_y)
    page.mouse.down(button="middle")
    page.mouse.move(start_x + dx, start_y + dy, steps=15)
    page.mouse.up(button="middle")
    page.wait_for_timeout(300)


def pan_node_into_view(page, node_name: str, target_x: int = 1250, target_y: int = 560, attempts: int = 8):
    """Pans the canvas so the parent node sits comfortably left of the node creator panel."""
    for _ in range(attempts):
        node = find_canvas_node(page, node_name)
        if not node:
            return False
        box = node.bounding_box()
        if not box:
            return False
        center_x = box['x'] + box['width'] / 2
        center_y = box['y'] + box['height'] / 2
        dx = int(target_x - center_x)
        dy = int(target_y - center_y)
        if abs(dx) <= 30 and abs(dy) <= 30:
            return True
        pan_canvas(page, max(-650, min(650, dx)), max(-450, min(450, dy)))
    return True


def capture_progressive_stages(page, workflow_id: str, plan: dict, article_path: str, images_dir: str, items: List[Dict], workflow_url: str):
    """Captures each node-selector screenshot against a canvas that only contains nodes built so far."""
    stages = plan.get("stages", [])
    available_alts = {item["alt_text"] for item in items}

    print(f"\n🧱 Capturing {len(stages)} progressive build stages...")
    live_workflow = rest_get_workflow(page, workflow_id)
    created_ids = []

    try:
        for index, stage in enumerate(stages, 1):
            alt = stage.get("alt", "")
            if alt not in available_alts:
                print(f"   ⏭️  [{index}/{len(stages)}] No article placeholder for: {alt}")
                continue

            payload = build_stage_payload(live_workflow, plan, index - 1)
            stage_id = rest_create_workflow(page, payload)
            created_ids.append(stage_id)

            page.goto(f"{N8N_BASE_URL}/workflow/{stage_id}", wait_until="networkidle")
            page.wait_for_timeout(2500)
            reset_zoom_to_100(page)
            ensure_100_percent_zoom(page)

            if stage.get("parent"):
                pan_node_into_view(page, stage["parent"])

            print(f"👉 [{index}/{len(stages)}] Stage canvas with {len(payload['nodes'])} node(s), adding '{stage['node']}'...")
            if not open_node_creator(page, stage.get("parent"), int(stage.get("output_index", 0))):
                print(f"   ⚠️ Node creator did not open for '{stage['node']}'")
                continue

            filename = screenshot_manager.sanitize_filename(alt)
            filepath = os.path.join(images_dir, filename)
            if capture_search_result(page, stage.get("search", stage["node"]), filepath, action=stage.get("action")):
                print(f"   ✅ Saved partial-canvas selector: images/{filename}")
    finally:
        # Return to the real workflow before deleting the temporary ones.
        try:
            page.goto(workflow_url, wait_until="networkidle")
            page.wait_for_timeout(1500)
        except Exception:
            pass
        for stage_id in created_ids:
            try:
                rest_delete_workflow(page, stage_id)
            except Exception as e:
                print(f"   ⚠️ Could not delete staging workflow {stage_id}: {e}")

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
                if b and b['width'] > 50 and b['height'] > 10:
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
    if "create spreadsheet" in nl:
        box = get_param_group_box(page, ['Title'])
    elif "create sheet" in nl:
        box = get_param_group_box(page, ['Document', 'Title'])
    elif "get row" in nl:
        if nl.endswith("1"):
            box = get_param_group_box(page, ['Document', 'Sheet', 'Filter', 'Column', 'Value'])
        else:
            box = get_param_group_box(page, ['Document', 'Sheet'])
    elif "asin" in nl or nl.startswith("read") or "keyword" in nl:
        box = get_param_group_box(page, ['Document', 'Sheet'])
    elif "loop" in nl:
        box = get_param_group_box(page, ['Batch Size'])
    elif "scrapehero" in nl:
        box = get_param_group_box(page, ['API', 'ASIN', 'Country Code', 'Keyword', 'Category URL', 'Best Seller'])
    elif "split out" in nl:
        box = get_param_group_box(page, ['Fields To Split Out'])
    elif "filter" in nl or "kept" in nl:
        box = get_param_group_box(page, ['condition'])
    elif nl == "if" or nl == "if1":
        box = get_param_group_box(page, ['condition'])
    elif "edit fields" in nl:
        box = get_param_group_box(page, ['Fields to Set', 'Count', 'Rank', 'ASIN'])
        if box:
            for inp in page.locator('.node-parameters-wrapper input').all():
                fb = inp.bounding_box()
                if fb and fb['y'] > box[1] + 20:
                    box = (box[0], int(fb['y'] - 12), box[2], box[3])
                    break
    elif "sort" in nl:
        box = get_param_group_box(page, ['Type', 'Order'])
    elif "update" in nl or "save deals" in nl or "append" in nl:
        box = get_param_group_box(page, ['Document', 'Sheet', 'Mapping Column Mode', 'Values to Send', 'Lowest New Price', 'ASIN', 'Product Name', 'Previous FBA Count', 'Columns', 'Rank'])
    elif "chat" in nl or "message" in nl:
        box = get_param_group_box(page, ['Space Name or ID', 'Text', 'Space'])
    elif "schedule trigger" in nl:
        box = get_param_group_box(page, ['Trigger Interval'])

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

def auto_capture_article(article_dir: str, workflow_id: Optional[str] = None, theme: str = "dark", progressive: Optional[bool] = None):
    article_path = screenshot_manager.find_article_file(article_dir)
    images_dir = os.path.join(os.path.dirname(article_path), "images")
    os.makedirs(images_dir, exist_ok=True)

    if not workflow_id:
        workflow_id = get_workflow_id(article_dir)

    if not workflow_id:
        print(f"Error: Could not determine workflow ID for {article_dir}.")
        return False

    capture_plan = load_capture_plan(os.path.dirname(article_path))
    if progressive is None:
        progressive = capture_plan is not None
    if progressive and not capture_plan:
        print("⚠️  Progressive capture requested but no capture_plan.json was found. Falling back to single-canvas capture.")
        progressive = False

    wf_url = f"{N8N_BASE_URL}/workflow/{workflow_id}"
    print(f"\n🚀 Automating live 1920x1080 browser capture for: {os.path.basename(article_dir)} [Theme: {theme.upper()}]")
    print(f"🔗 Target: {wf_url}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            executable_path=CHROME_BIN if os.path.exists(CHROME_BIN) else None,
            headless=True,
            color_scheme=theme,
            viewport={"width": 1920, "height": 1080}
        )
        if os.path.exists(AUTH_STATE_PATH):
            try:
                with open(AUTH_STATE_PATH, 'r', encoding='utf-8') as f:
                    auth_state = json.load(f)
                cookies = auth_state.get("cookies", [])
                if cookies:
                    context.add_cookies(cookies)
                    print(f"🔑 Restored {len(cookies)} auth cookie(s) from {os.path.basename(AUTH_STATE_PATH)}")
            except Exception as e:
                print(f"⚠️  Could not restore auth state: {e}")

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(wf_url, wait_until="networkidle")
        page.wait_for_timeout(3500)

        password_input = page.locator('input[type="password"]').first
        if "/signin" in page.url or (password_input.count() > 0 and password_input.is_visible()):
            print("❌ Authentication failed. Please log in first.")
            print("   Run: python3 utils/login_window.py")
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
        if progressive:
            capture_progressive_stages(page, workflow_id, capture_plan, article_path, images_dir, items, wf_url)
            page.keyboard.press("1")
            page.wait_for_timeout(1000)
        else:
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
                    edit_btn = page.locator('[data-test-id="credential-edit-button"], [data-test-id="node-credentials-empty-state"], button:has-text("Connect to ScrapeHero"), div:has-text("Connect to ScrapeHero")').first
                    if edit_btn.count() > 0:
                        edit_btn.click()
                        page.wait_for_timeout(1500)

                        key_input = page.locator('input[type="password"], input[name*="apiKey"], input[placeholder*="key" i]').first
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

        # Exact alt-text matches for nodes whose generic keywords would also
        # match other screenshots in the same article (category logger).
        specific_alt_patterns = {
            "Get row(s) in sheet": ["read category urls"],
            "Get row(s) in sheet1": ["filter the category row"],
            "Create spreadsheet": ["create a category spreadsheet"],
            "Update row in sheet": ["save the tracking spreadsheet id"],
            "Create sheet": ["create a dated tab"],
            "Append row in sheet": ["append best seller ranks"],
            "If": ["check for an existing tracking spreadsheet"],
        }
        available_specifics = {
            name: pats
            for name, pats in specific_alt_patterns.items()
            if any(p in it["alt_text"].lower() for it in items for p in pats)
        }

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
                        if node_name in available_specifics:
                            if any(p in alt_l for p in available_specifics[node_name]):
                                matched_items.append(it)
                            continue
                        if "get row" in node_name.lower():
                            if node_name.endswith("1"):
                                if "filter" in alt_l or "category row" in alt_l or "tracking" in alt_l:
                                    matched_items.append(it)
                            elif "read" in alt_l or "category url" in alt_l:
                                matched_items.append(it)
                        elif "asin" in node_name.lower() and "asin" in alt_l:
                            matched_items.append(it)
                        elif "create spreadsheet" in node_name.lower() and "spreadsheet" in alt_l:
                            matched_items.append(it)
                        elif "create sheet" in node_name.lower() and ("create sheet" in alt_l or "dated tab" in alt_l):
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
                        elif node_name == "If" and ("if node" in alt_l and ("active" in alt_l or "exist" in alt_l or "check" in alt_l)):
                            matched_items.append(it)
                        elif node_name == "If1" and ("if node" in alt_l and ("detect" in alt_l or "change" in alt_l or "count" in alt_l)):
                            matched_items.append(it)
                        elif "edit fields" in node_name.lower() and "edit fields" in alt_l:
                            matched_items.append(it)
                        elif "sort" in node_name.lower() and "sort" in alt_l:
                            matched_items.append(it)
                        elif "update" in node_name.lower() and ("update" in alt_l or "save" in alt_l or "lowest price" in alt_l):
                            matched_items.append(it)
                        elif "append" in node_name.lower() and ("append" in alt_l or "dated tab" in alt_l or "updated fba" in alt_l):
                            matched_items.append(it)
                        elif ("message" in node_name.lower() or "chat" in node_name.lower()) and ("chat" in alt_l or "message" in alt_l or "alert" in alt_l):
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
    parser.add_argument("--progressive", action="store_true", help="Capture selector screenshots stage by stage from capture_plan.json")
    args = parser.parse_args()

    article_dir = args.article
    if not os.path.exists(article_dir):
        cand = os.path.join(ROOT_DIR, "articles", article_dir)
        if os.path.exists(cand):
            article_dir = cand

    auto_capture_article(article_dir, args.workflow_id, args.theme, progressive=args.progressive or None)

if __name__ == "__main__":
    main()
