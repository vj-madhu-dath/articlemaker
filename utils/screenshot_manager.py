#!/usr/bin/env python3
"""
Screenshot Manager for ScrapeHero Article Maker.
Automates discovering, matching, syncing, capturing, and marking up screenshots
for n8n tutorials and articles.
"""

import os
import sys
import re
import json
import shutil
import subprocess
import argparse
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UTILS_DIR = os.path.join(ROOT_DIR, "utils")
TEMPLATES_DIR = os.path.join(ROOT_DIR, "templates")
COMMON_DIR = os.path.join(TEMPLATES_DIR, "common_screenshots")
CATALOG_FILE = os.path.join(COMMON_DIR, "catalog.json")
CLIP_SAVE_BIN = os.path.join(UTILS_DIR, "clip_save")
OCR_BIN = os.path.join(UTILS_DIR, "ocr_detector")

# Import markup_helper if available
sys.path.insert(0, UTILS_DIR)
try:
    import markup_helper
except ImportError:
    markup_helper = None

IMAGE_MD_REGEX = re.compile(r'!\[([^\]]*)\]\(([^)]*)\)')

def load_catalog() -> Dict[str, Any]:
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"entries": []}

def save_catalog(catalog: Dict[str, Any]):
    os.makedirs(COMMON_DIR, exist_ok=True)
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2)

def find_article_file(article_dir_or_file: str) -> str:
    """Resolves the path to article.md from either a folder or file path."""
    if os.path.isfile(article_dir_or_file):
        return os.path.abspath(article_dir_or_file)
    candidates = [
        os.path.join(article_dir_or_file, "article.md"),
        os.path.join(article_dir_or_file, "Article.md")
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    if os.path.isdir(article_dir_or_file):
        for f in os.listdir(article_dir_or_file):
            if f.endswith(".md") and not f.startswith("seo_"):
                return os.path.abspath(os.path.join(article_dir_or_file, f))
    raise FileNotFoundError(f"Could not find article markdown file in: {article_dir_or_file}")

def sanitize_filename(alt_text: str) -> str:
    """Creates a standardized filename from alt text."""
    clean = alt_text.strip()
    clean = re.sub(r'[\\/*?:"<>|]', '', clean)
    clean = re.sub(r'\s+', ' ', clean)
    if not clean.lower().endswith(('.png', '.jpg', '.jpeg')):
        clean += ".png"
    return clean

def parse_article_images(article_path: str) -> List[Dict[str, Any]]:
    """Parses markdown file and returns all image placeholders with their status."""
    article_dir = os.path.dirname(article_path)
    catalog = load_catalog()
    entries = catalog.get("entries", [])

    results = []
    with open(article_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_idx, line in enumerate(lines):
        for match in IMAGE_MD_REGEX.finditer(line):
            alt_text = match.group(1).strip()
            url = match.group(2).strip()
            
            exists = False
            resolved_path = None
            if url:
                target_path = os.path.normpath(os.path.join(article_dir, url))
                if os.path.exists(target_path):
                    exists = True
                    resolved_path = target_path

            # Check for workflow overview match
            is_workflow_overview = bool(re.search(r'complete.*workflow|full.*workflow|workflow overview', alt_text, re.IGNORECASE))

            # Check for catalog match
            catalog_match = None
            for entry in entries:
                for pat in entry.get("patterns", []):
                    if re.search(pat, alt_text, re.IGNORECASE):
                        catalog_match = entry
                        break
                if catalog_match:
                    break

            results.append({
                "index": len(results) + 1,
                "line_idx": line_idx,
                "alt_text": alt_text,
                "url": url,
                "exists": exists,
                "resolved_path": resolved_path,
                "is_workflow_overview": is_workflow_overview,
                "catalog_match": catalog_match,
                "raw_match": match.group(0)
            })

    return results

def render_workflow_overview_image(article_dir: str, out_filename: Optional[str] = None) -> Optional[str]:
    """Renders a clean, high-DPI canvas overview of workflow.json."""
    wf_path = os.path.join(article_dir, "workflow.json")
    if not os.path.exists(wf_path):
        return None

    with open(wf_path, 'r', encoding='utf-8') as f:
        wf = json.load(f)

    nodes = wf.get("nodes", [])
    if not nodes:
        return None

    images_dir = os.path.join(article_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    if not out_filename:
        out_filename = "The complete n8n workflow overview.png"
    out_path = os.path.join(images_dir, out_filename)

    xs = [n.get("position", [0, 0])[0] for n in nodes]
    ys = [n.get("position", [0, 0])[1] for n in nodes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    node_w, node_h = 240, 90
    padding_x, padding_y = 120, 120

    canvas_w = int((max_x - min_x) + node_w + padding_x * 2)
    canvas_h = int((max_y - min_y) + node_h + padding_y * 2)
    canvas_w = max(canvas_w, 1200)
    canvas_h = max(canvas_h, 600)

    BG = (248, 249, 250)
    CARD_BG = (255, 255, 255)
    CARD_BORDER = (226, 232, 240)
    TEXT_MAIN = (15, 23, 42)
    TEXT_SUB = (100, 116, 139)
    WIRE_COLOR = (148, 163, 184)
    CORAL = (255, 109, 90)

    img = Image.new("RGBA", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(img)

    for x in range(20, canvas_w, 24):
        for y in range(20, canvas_h, 24):
            draw.point((x, y), fill=(215, 220, 230))

    def map_pos(pos):
        x = int(pos[0] - min_x + padding_x)
        y = int(pos[1] - min_y + padding_y)
        return x, y

    node_pos_map = {}
    for node in nodes:
        name = node.get("name", "Node")
        pos = node.get("position", [0, 0])
        nx, ny = map_pos(pos)
        node_pos_map[name] = (nx, ny)

    connections = wf.get("connections", {})
    for src_name, conn_data in connections.items():
        if src_name not in node_pos_map:
            continue
        sx, sy = node_pos_map[src_name]
        src_pt = (sx + node_w, sy + node_h // 2)

        for branch_type, branches in conn_data.items():
            for branch in branches:
                for target_info in branch:
                    tgt_name = target_info.get("node")
                    if tgt_name in node_pos_map:
                        tx, ty = node_pos_map[tgt_name]
                        tgt_pt = (tx, ty + node_h // 2)
                        
                        mid_x = (src_pt[0] + tgt_pt[0]) // 2
                        draw.line([src_pt, (mid_x, src_pt[1]), (mid_x, tgt_pt[1]), tgt_pt], fill=WIRE_COLOR, width=3)
                        draw.ellipse([src_pt[0] - 5, src_pt[1] - 5, src_pt[0] + 5, src_pt[1] + 5], fill=CORAL)
                        draw.ellipse([tgt_pt[0] - 5, tgt_pt[1] - 5, tgt_pt[0] + 5, tgt_pt[1] + 5], fill=WIRE_COLOR)

    for node in nodes:
        name = node.get("name", "Node")
        ntype = node.get("type", "").split(".")[-1]
        nx, ny = node_pos_map[name]

        for s in range(4, 0, -1):
            draw.rounded_rectangle([nx - s, ny - s, nx + node_w + s, ny + node_h + s], radius=10, fill=(0, 0, 0, int(10 / s)))
        
        draw.rounded_rectangle([nx, ny, nx + node_w, ny + node_h], radius=8, fill=CARD_BG, outline=CARD_BORDER, width=2)
        draw.rounded_rectangle([nx, ny, nx + 6, ny + node_h], radius=3, fill=CORAL)

        draw.text((nx + 18, ny + 16), name, fill=TEXT_MAIN)
        draw.text((nx + 18, ny + 46), f"type: {ntype}", fill=TEXT_SUB)

    draw.text((30, 30), f"n8n Workflow: {wf.get('name', 'Automation')}", fill=TEXT_MAIN)
    draw.text((30, 52), f"Total nodes: {len(nodes)} | ScrapeHero Automation Pipeline", fill=TEXT_SUB)

    img.save(out_path)
    return out_path

def sync_common_screenshots(article_path: str) -> Dict[str, Any]:
    """Syncs missing placeholders from common catalog and renders workflow diagram."""
    article_dir = os.path.dirname(article_path)
    images_dir = os.path.join(article_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    items = parse_article_images(article_path)
    with open(article_path, 'r', encoding='utf-8') as f:
        content = f.read()

    synced_count = 0
    synced_items = []

    for item in items:
        if item["exists"]:
            continue

        # Handle Workflow Overview auto-generation
        if item["is_workflow_overview"]:
            wf_filename = sanitize_filename(item["alt_text"])
            rendered = render_workflow_overview_image(article_dir, wf_filename)
            if rendered:
                old_tag = item["raw_match"]
                new_tag = f"![{item['alt_text']}](images/{wf_filename})"
                content = content.replace(old_tag, new_tag, 1)
                synced_count += 1
                synced_items.append({
                    "alt_text": item["alt_text"],
                    "filename": wf_filename,
                    "source": "workflow.json auto-render"
                })
                continue

        # Handle Catalog match
        match = item["catalog_match"]
        if match:
            src_file = os.path.join(COMMON_DIR, match["filename"])
            if os.path.exists(src_file):
                dst_filename = sanitize_filename(item["alt_text"])
                dst_file = os.path.join(images_dir, dst_filename)
                
                shutil.copy2(src_file, dst_file)
                
                old_tag = item["raw_match"]
                new_tag = f"![{item['alt_text']}](images/{dst_filename})"
                content = content.replace(old_tag, new_tag, 1)
                
                synced_count += 1
                synced_items.append({
                    "alt_text": item["alt_text"],
                    "filename": dst_filename,
                    "source": "common catalog"
                })

    with open(article_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {
        "synced_count": synced_count,
        "synced_items": synced_items,
        "total_images": len(items)
    }

def capture_from_clipboard(out_path: str) -> bool:
    """Extracts image data from macOS clipboard using clip_save binary."""
    if not os.path.exists(CLIP_SAVE_BIN):
        return False
    res = subprocess.run([CLIP_SAVE_BIN, out_path], capture_output=True, text=True)
    return res.returncode == 0 and os.path.exists(out_path)

def run_ocr_on_image(image_path: str) -> List[Dict[str, Any]]:
    """Runs native Apple Vision OCR on an image and returns words/bounding boxes."""
    if not os.path.exists(OCR_BIN):
        return []
    img_dir = os.path.dirname(image_path)
    img_name = os.path.basename(image_path)
    subprocess.run([OCR_BIN, img_dir], capture_output=True, text=True)
    ocr_json = "ocr_results.json"
    if os.path.exists(ocr_json):
        try:
            with open(ocr_json, 'r') as f:
                data = json.load(f)
            for item in data:
                if item.get("filename") == img_name:
                    return item.get("elements", [])
        finally:
            if os.path.exists(ocr_json):
                os.remove(ocr_json)
    return []

def apply_auto_arrow_to_keyword(image_path: str, keyword: str, direction: str = "right") -> bool:
    """Finds keyword in image via OCR and draws a standard red arrow pointing to it."""
    if not markup_helper:
        return False

    elements = run_ocr_on_image(image_path)
    target = None
    for el in elements:
        if keyword.lower() in el.get("text", "").lower():
            target = el
            break

    if target:
        tx = target["x"]
        ty = target["y"] + target["h"] // 2
        markup_helper.draw_arrow(image_path, tip_x=tx - 10, tip_y=ty, direction="right", out_path=image_path)
        print(f"🎯 Auto-marked arrow pointing to '{target['text']}' at ({tx}, {ty})")
        return True
    else:
        print(f"⚠️ Keyword '{keyword}' not found in OCR elements. Arrow skipped.")
        return False

def add_single_screenshot(article_path: str, image_source: str, alt_text: Optional[str] = None, arrow_target: Optional[str] = None):
    """Directly adds a screenshot from disk/clipboard, applies markup, and links in article.md."""
    article_dir = os.path.dirname(article_path)
    images_dir = os.path.join(article_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    items = parse_article_images(article_path)
    target_item = None

    if alt_text:
        for it in items:
            if it["alt_text"].lower() == alt_text.lower():
                target_item = it
                break

    if not target_item:
        missing = [it for it in items if not it["exists"]]
        if missing:
            target_item = missing[0]

    if not target_item:
        print("❌ No matching or missing placeholder found in article.md.")
        return False

    filename = sanitize_filename(target_item["alt_text"])
    dest_path = os.path.join(images_dir, filename)

    if image_source == "clipboard":
        success = capture_from_clipboard(dest_path)
        if not success:
            print("❌ No image in clipboard.")
            return False
    else:
        if not os.path.exists(image_source):
            print(f"❌ Source image {image_source} not found.")
            return False
        shutil.copy2(image_source, dest_path)

    if arrow_target:
        apply_auto_arrow_to_keyword(dest_path, arrow_target)

    with open(article_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_tag = target_item["raw_match"]
    new_tag = f"![{target_item['alt_text']}](images/{filename})"
    content = content.replace(old_tag, new_tag, 1)

    with open(article_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Successfully linked: images/{filename}")
    return True

def interactive_capture_session(article_path: str):
    """Guides user through remaining missing screenshots with clipboard capture."""
    article_dir = os.path.dirname(article_path)
    images_dir = os.path.join(article_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    items = parse_article_images(article_path)
    missing = [it for it in items if not it["exists"]]

    if not missing:
        print("🎉 All screenshots are already present in this article!")
        return

    print(f"\n========================================================")
    print(f"📸 Interactive Quick-Capture Session ({len(missing)} images remaining)")
    print(f"========================================================")
    print("Tips:")
    print("  - On Mac, press [Cmd + Ctrl + Shift + 4] to copy a screen selection to clipboard.")
    print("  - Once copied, simply press [ENTER] in this terminal to auto-save and link it!")
    print("  - Type 'skip' to skip to the next image, or 'quit' to exit.\n")

    with open(article_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for idx, item in enumerate(missing, 1):
        print(f"\n[{idx}/{len(missing)}] Target: \"{item['alt_text']}\"")
        filename = sanitize_filename(item["alt_text"])
        out_path = os.path.join(images_dir, filename)

        user_input = input("👉 Ready? Press [ENTER] after copying to clipboard (or enter file path / 'skip'): ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if user_input.lower() == "skip":
            continue

        captured = False
        if user_input and os.path.exists(user_input):
            shutil.copy2(user_input, out_path)
            captured = True
        else:
            success = capture_from_clipboard(out_path)
            if success:
                captured = True
            else:
                print("❌ No image found in clipboard! Make sure you copied an image.")
                retry = input("Try again? [ENTER] to retry, or 'skip': ").strip()
                if retry.lower() != "skip":
                    if capture_from_clipboard(out_path):
                        captured = True

        if captured:
            kw = input("🎯 Add red arrow? (Enter button/field text, or press ENTER to skip): ").strip()
            if kw:
                apply_auto_arrow_to_keyword(out_path, kw)

            old_tag = item["raw_match"]
            new_tag = f"![{item['alt_text']}](images/{filename})"
            content = content.replace(old_tag, new_tag, 1)
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ Saved & linked: images/{filename}")

    print("\n✅ Session complete!")

def list_screenshots(article_path: str):
    """Prints a clear summary list of all screenshot placeholders in the article."""
    items = parse_article_images(article_path)
    print(f"\n📸 Screenshot Status for: {os.path.basename(article_path)}")
    print("=" * 80)
    print(f"{'#':<3} | {'Status':<10} | {'Type':<12} | {'Placeholder / Alt Text'}")
    print("-" * 80)
    
    missing_count = 0
    synced_count = 0
    present_count = 0

    for item in items:
        if item["exists"]:
            status = "✅ Present"
            itype = "Custom/Local"
            present_count += 1
        elif item["is_workflow_overview"]:
            status = "⚡ Workflow"
            itype = "Auto-Render"
            synced_count += 1
        elif item["catalog_match"]:
            status = "⚡ Matched"
            itype = "CommonCatalog"
            synced_count += 1
        else:
            status = "❌ Missing"
            itype = "Custom"
            missing_count += 1

        print(f"{item['index']:<3} | {status:<10} | {itype:<12} | {item['alt_text'][:55]}")

    print("=" * 80)
    print(f"Total: {len(items)} | Present: {present_count} | Ready to Auto-Sync: {synced_count} | Missing: {missing_count}\n")

def register_common_screenshot(image_path: str, key: str, title: str, pattern: str):
    """Registers an image into the common screenshots catalog for future reuse."""
    if not os.path.exists(image_path):
        print(f"Error: {image_path} does not exist.")
        return False
    
    filename = os.path.basename(image_path)
    dest_path = os.path.join(COMMON_DIR, filename)
    shutil.copy2(image_path, dest_path)

    catalog = load_catalog()
    entries = catalog.setdefault("entries", [])
    
    # Check if key exists
    updated = False
    for entry in entries:
        if entry["key"] == key:
            entry["title"] = title
            entry["filename"] = filename
            if pattern not in entry.get("patterns", []):
                entry.setdefault("patterns", []).append(pattern)
            updated = True
            break
            
    if not updated:
        entries.append({
            "key": key,
            "title": title,
            "filename": filename,
            "patterns": [pattern]
        })

    save_catalog(catalog)
    print(f"✅ Registered common screenshot: '{title}' ({filename})")
    return True

def main():
    parser = argparse.ArgumentParser(description="Manage tutorial screenshots for articles.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List screenshots and status in article")
    p_list.add_argument("article", help="Article directory or article.md path")

    # sync
    p_sync = subparsers.add_parser("sync", help="Auto-sync matching screenshots from common catalog")
    p_sync.add_argument("article", help="Article directory or article.md path")

    # capture
    p_cap = subparsers.add_parser("capture", help="Interactive clipboard quick-capture session")
    p_cap.add_argument("article", help="Article directory or article.md path")

    # add
    p_add = subparsers.add_parser("add", help="Add a specific image to article")
    p_add.add_argument("article", help="Article directory or article.md path")
    p_add.add_argument("image", help="Image path or 'clipboard'")
    p_add.add_argument("--alt", default=None, help="Specific alt text to match")
    p_add.add_argument("--arrow-target", default=None, help="Text to detect via OCR and point arrow to")

    # register-common
    p_reg = subparsers.add_parser("register-common", help="Register a screenshot into common catalog")
    p_reg.add_argument("image", help="Path to image file")
    p_reg.add_argument("key", help="Unique key (e.g. manual_trigger)")
    p_reg.add_argument("title", help="Title / Alt text")
    p_reg.add_argument("pattern", help="Regex pattern to match in alt text")

    args = parser.parse_args()

    if args.command == "list":
        article_path = find_article_file(args.article)
        list_screenshots(article_path)
    elif args.command == "sync":
        article_path = find_article_file(args.article)
        res = sync_common_screenshots(article_path)
        print(f"✅ Synced {res['synced_count']} / {res['total_images']} screenshots for {os.path.basename(article_path)}:")
        for item in res["synced_items"]:
            print(f"   - [{item['source']}] {item['filename']}")
    elif args.command == "capture":
        article_path = find_article_file(args.article)
        interactive_capture_session(article_path)
    elif args.command == "add":
        article_path = find_article_file(args.article)
        add_single_screenshot(article_path, args.image, args.alt, args.arrow_target)
    elif args.command == "register-common":
        register_common_screenshot(args.image, args.key, args.title, args.pattern)

if __name__ == "__main__":
    main()
