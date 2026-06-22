from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="en-US",
        timezone_id="America/Los_Angeles",
        viewport={"width": 1280, "height": 720},
    )
    with Stealth().use_sync(context):
        page = context.new_page()
        response = page.goto("https://bidnetdirect.com/login", wait_until="networkidle")
        print("Status:", response.status)
        print("Title:", page.title())
        page.screenshot(path="debug.png")

    browser.close()