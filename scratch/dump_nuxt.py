import asyncio
import json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Goto search page...")
        await page.goto("https://www.upwork.com/nx/search/jobs/?q=python", wait_until="domcontentloaded")
        
        # Get __NUXT__
        nuxt = await page.evaluate("() => window.__NUXT__")
        
        with open("nuxt_dump.json", "w") as f:
            json.dump(nuxt, f, indent=2)
            
        print("Saved to nuxt_dump.json")
        await browser.close()

asyncio.run(run())
