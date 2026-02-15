from playwright.sync_api import sync_playwright
import time
import os

def debug_dashboard():
    print("Debugging Dashboard Loading...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 720})

        page.goto("http://localhost:8010/#dashboard")

        # Take a screenshot of what IS visible
        time.sleep(2)
        page.screenshot(path="debug_dashboard.png")
        print("Captured debug_dashboard.png")

        # Check if the element exists in DOM even if hidden
        exists = page.evaluate("!!document.getElementById('page-dashboard')")
        print(f"Element #page-dashboard exists: {exists}")

        # Check classes
        classes = page.evaluate("document.getElementById('page-dashboard')?.className")
        print(f"Classes: {classes}")

        # Check if router ran
        # If router ran, it should remove 'hidden' class based on hash

        browser.close()

if __name__ == "__main__":
    debug_dashboard()
