from selenium import webdriver
from axe_selenium_python import Axe
import json
import pandas as pd
import yaml
import os
from datetime import datetime

# ----------------------------
# Helpers
# ----------------------------

def load_guidance(path="guidance.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def enrich_violations(violations, guidance):
    enriched = []
    for v in violations:
        rule_id = v.get("id")
        v["expert_guidance"] = guidance.get(rule_id)
        enriched.append(v)
    return enriched

def flatten_violations(violations):
    rows = []
    for v in violations:
        for node in v.get("nodes", []):
            rows.append({
                "rule_id": v.get("id"),
                "description": v.get("description"),
                "help": v.get("help"),
                "helpUrl": v.get("helpUrl"),
                "impact": v.get("impact"),
                "tags": v.get("tags"),
                "target": " ".join(node.get("target", [])),
                "html": node.get("html"),
                "failureSummary": node.get("failureSummary"),
            })
    return rows

def enrich_findings(findings, guidance):
    for row in findings:
        g = guidance.get(row["rule_id"], {})
        row["why_it_matters"] = g.get("why_it_matters")
        row["recommended_fix"] = g.get("recommended_fix")
        row["coaching_tip"] = g.get("coaching_tip")
    return findings

# ----------------------------
# Main Prototype
# ----------------------------

# Load guidance
guidance = load_guidance("guidance.yaml")

# Input URLs (can also load from JSON/YAML file)
urls = [
    "http://max-data.com",
    "https://max-data.com/Mds3/JobPortal"
]

# Setup Chrome driver
driver = webdriver.Chrome()

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = f"axe_scan_results_{timestamp}"
os.makedirs(output_dir, exist_ok=True)

for url in urls:
    try:
        print(f"Scanning {url} ...")
        driver.get(url)

        # Run axe scan
        axe = Axe(driver)
        axe.inject()
        results = axe.run()
        
        # Save raw JSON
        json_file = os.path.join(output_dir, f"{url.replace('://','_').replace('/','_')}_raw.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)

        # Flatten + enrich
        violations = results.get("violations", [])
        flattened = flatten_violations(violations)
        enriched = enrich_findings(flattened, guidance)

        # Save CSV
        df = pd.DataFrame(enriched)
        csv_file = os.path.join(output_dir, f"{url.replace('://','_').replace('/','_')}_enriched.csv")
        df.to_csv(csv_file, index=False)

        # Screenshot
        screenshot_file = os.path.join(output_dir, f"{url.replace('://','_').replace('/','_')}_screenshot.png")
        driver.save_screenshot(screenshot_file)

        print(f"Completed scan for {url}. Results saved in {output_dir}")

    except Exception as e:
        print(f"Error scanning {url}: {e}")

driver.quit()
print("All scans completed successfully!")
