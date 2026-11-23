"""Start the Streamlit dashboard headlessly and save screenshots to reports/figures/dashboard/.

    pip install -e ".[app]" playwright && playwright install --with-deps chromium
    python scripts/screenshot_dashboard.py

Used by the Analysis workflow so the README images always match the current model.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures" / "dashboard"
PORT = 8599
# (file name, mode label, number of days to step back from the last day)
SHOTS = [
    ("rail_2024-07-31.png", "Rail (metro, Marmaray, tram)", 0),
    ("road_holiday_2024-06-17.png", "Road (bus, metrobus)", 44),
]


async def capture() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=1.5)
        await page.goto(f"http://localhost:{PORT}", wait_until="networkidle")
        await page.wait_for_selector("text=Actual passengers", timeout=300_000)
        print("app loaded", flush=True)
        for name, mode, steps in SHOTS:
            await page.get_by_role("combobox").first.click()
            await page.get_by_role("option", name=mode).click()
            await page.wait_for_timeout(2000)
            slider = page.get_by_role("slider")
            await slider.focus()
            for _ in range(steps):
                await page.keyboard.press("ArrowLeft")
            await page.wait_for_timeout(8000)  # retrain + redraw
            await page.screenshot(path=str(OUT / name), full_page=True)
            day = await slider.get_attribute("aria-valuetext")
            print(f"saved {name} ({mode}, {day})", flush=True)
        await browser.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
                               "--server.headless", "true", "--server.port", str(PORT)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(8)
        asyncio.run(capture())
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
