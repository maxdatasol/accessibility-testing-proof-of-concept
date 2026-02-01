import os
import yaml
from datetime import datetime

# Choose mode: "selenium" or "playwright"
SCAN_MODE = "playwright"  # change to "selenium" to use Selenium version

# URLs to scan
URLS = [
    "https://max-data.com/Mds3/JobPortal",
    "http://max-data.com"
]

# Guidance file for enrichment
GUIDANCE_FILE = "guidance.yaml"

# ----------------------------
# Helper to load guidance
# ----------------------------
def load_guidance(path=GUIDANCE_FILE):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# ----------------------------
# Import runner based on mode
# ----------------------------
if SCAN_MODE == "selenium":
    from scans.selenium_runner import main as runner_main
elif SCAN_MODE == "playwright":
    from scans.playwriter_runner import main as runner_main
else:
    raise ValueError("SCAN_MODE must be 'selenium' or 'playwright'")

# ----------------------------
# Prepare output folder
# ----------------------------
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = f"axe_scan_results_{timestamp}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# Run the scans
# ----------------------------
guidance = load_guidance(GUIDANCE_FILE)

# For Playwright (async), use asyncio.run
if SCAN_MODE == "playwright":
    import asyncio
    asyncio.run(runner_main(URLS))
else:
    runner_main(URLS)

print(f"All scans completed. Results in folder: {OUTPUT_DIR}")
