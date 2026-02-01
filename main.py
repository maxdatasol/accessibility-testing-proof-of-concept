from selenium import webdriver
from axe_selenium_python import Axe
import json
import pandas as pd
import yaml

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
# Main
# ----------------------------

# Setup browser
driver = webdriver.Chrome()

# Target URL
url = "http://max-data.com"
driver.get(url)

# Run axe-core accessibility scan
axe = Axe(driver)
axe.inject()
results = axe.run()

# Save raw JSON
with open("axe_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4)

# Load guidance
guidance = load_guidance("guidance.yaml")

# Enrich violations
violations = results.get("violations", [])

flattened = flatten_violations(violations)
enriched = enrich_findings(flattened, guidance)

df = pd.DataFrame(enriched)
df.to_csv("violations_enriched_flat.csv", index=False)


# Optional screenshot
driver.save_screenshot("screenshot.png")

driver.quit()

print("POC completed successfully with expert guidance!")
