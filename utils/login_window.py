import os
import json
from playwright.sync_api import sync_playwright

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(ROOT_DIR, ".n8n_browser_profile")
AUTH_STATE = os.path.join(PROFILE_DIR, "auth_state.json")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=False,
        color_scheme="dark",
        viewport={"width": 1920, "height": 1080},
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("http://localhost:5678/signin", wait_until="networkidle")
    page.bring_to_front()
    print("Login window open. Waiting for authentication...", flush=True)
    for _ in range(600):
        if "/signin" not in page.url:
            print(f"LOGIN_SUCCESS {page.url}", flush=True)
            break
        page.wait_for_timeout(1000)
    else:
        print("LOGIN_TIMEOUT", flush=True)

    if "/signin" not in page.url:
        state = context.storage_state()
        with open(AUTH_STATE, "w", encoding="utf-8") as f:
            json.dump(state, f)
        print(f"AUTH_STATE_SAVED {AUTH_STATE}", flush=True)
        for cookie in state.get("cookies", []):
            print(f"COOKIE {cookie.get('name')} expires={cookie.get('expires')}", flush=True)

    context.close()
