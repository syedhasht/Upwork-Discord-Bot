import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        page.on("request", lambda req: print(f"REQ: {req.url}\nPAYLOAD: {req.post_data}") if "graphql" in req.url else None)
        
        print("Goto search page...")
        await page.goto("https://www.upwork.com/nx/search/jobs/?q=python", wait_until="networkidle")
        print("Scrolling...")
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(2)
        print("Clicking next page...")
        await page.goto("https://www.upwork.com/nx/search/jobs/?q=python&page=2", wait_until="networkidle")
        await asyncio.sleep(2)
        
        await browser.close()

asyncio.run(run())
