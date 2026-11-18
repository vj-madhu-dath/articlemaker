from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=".n8n_browser_profile",
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=False,
        color_scheme="dark",
        viewport={"width": 1920, "height": 1080},
        args=["--no-sandbox"],
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
    context.close()
