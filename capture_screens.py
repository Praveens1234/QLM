import asyncio
from playwright.async_api import async_playwright
import time
import os

SCREENSHOT_DIR = "public/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def capture_screenshots():
    print(f"Saving screenshots to {SCREENSHOT_DIR}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a high-resolution viewport for "Professional" look
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. Dashboard
        print("Capturing Dashboard...")
        await page.goto("http://localhost:8000/#dashboard")
        await page.wait_for_selector("h2 >> text=Dashboard")
        await asyncio.sleep(2) # Wait for animations
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_dashboard.png", full_page=True)

        # 2. Data Manager
        print("Capturing Data Manager...")
        await page.goto("http://localhost:8000/#data")
        await page.wait_for_selector("h2 >> text=Data Manager")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/02_data_manager.png", full_page=True)

        # 3. Strategy Lab
        print("Capturing Strategy Lab...")
        await page.goto("http://localhost:8000/#strategies")
        await page.wait_for_selector("h2 >> text=Strategy Lab")
        await asyncio.sleep(2) # Wait for Monaco
        await page.screenshot(path=f"{SCREENSHOT_DIR}/03_strategy_lab.png", full_page=True)

        # 4. Backtest Runner
        print("Capturing Backtest Runner...")
        await page.goto("http://localhost:8000/#backtest")
        await page.wait_for_selector("h2 >> text=Backtest Runner")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/04_backtest_runner.png", full_page=True)

        # 5. AI Assistant
        print("Capturing AI Assistant...")
        await page.goto("http://localhost:8000/#assistant")
        await page.wait_for_selector("span >> text=QLM Assistant")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/05_ai_assistant.png", full_page=True)

        # 6. Mobile View (Dashboard)
        print("Capturing Mobile Dashboard...")
        await page.set_viewport_size({"width": 375, "height": 812})
        await page.goto("http://localhost:8000/#dashboard")
        await asyncio.sleep(1)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/06_mobile_dashboard.png")

        print("Capture Complete.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_screenshots())
