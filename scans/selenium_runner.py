# selenium_runner.py
from selenium import webdriver
from axe_selenium_python import Axe
import subprocess, json, os
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import yaml

# ----------------------------
# Helpers
# ----------------------------
def load_guidance(path="guidance.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

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
        row["why_it_matters"] = g.get("why_it_matters", "")
        row["recommended_fix"] = g.get("recommended_fix", "")
        row["coaching_tip"] = g.get("coaching_tip", "")
    return findings

# ----------------------------
# PDF Reporting
# ----------------------------
class AuditPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Accessibility Audit Report', ln=True, align='C')
        self.ln(5)

    def add_summary(self, url, total_violations, lighthouse_score=None):
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f"URL Scanned: {url}", ln=True)
        self.cell(0, 10, f"Total Violations: {total_violations}", ln=True)
        if lighthouse_score is not None:
            self.cell(0, 10, f"Lighthouse Accessibility Score: {lighthouse_score}", ln=True)
        self.ln(5)

    def add_violation_table(self, violations, max_rows=10):
        self.set_font('Arial', 'B', 10)
        self.cell(30, 8, 'Rule ID', 1)
        self.cell(30, 8, 'Impact', 1)
        self.cell(60, 8, 'Description', 1)
        self.cell(60, 8, 'Recommendation', 1)
        self.ln()
        self.set_font('Arial', '', 10)
        for i, v in enumerate(violations):
            if i >= max_rows:
                break
            self.cell(30, 8, v.get('rule_id',''), 1)
            self.cell(30, 8, v.get('impact',''), 1)
            self.cell(60, 8, v.get('description','')[:50], 1)
            self.cell(60, 8, v.get('recommended_fix','')[:50], 1)
            self.ln()
        self.ln(5)

    def add_screenshot(self, path):
        self.add_page()
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Screenshot', ln=True)
        self.image(path, x=10, y=25, w=180)
        self.ln(5)

# ----------------------------
# Runner
# ----------------------------
def run_lighthouse(url, output_path):
    """Run Lighthouse CLI, return accessibility score"""
    try:
        subprocess.run([
            "lighthouse",
            url,
            "--output=json",
            f"--output-path={output_path}",
            "--quiet",
            "--chrome-flags='--headless'"
        ], check=True)
        with open(output_path, "r") as f:
            data = json.load(f)
        score = data["categories"]["accessibility"]["score"] * 100
        return score
    except Exception as e:
        print(f"Lighthouse error for {url}: {e}")
        return None

def scan_url(url, guidance, driver, output_dir):
    print(f"Scanning {url} ...")
    driver.get(url)

    # Run axe-core
    axe = Axe(driver)
    axe.inject()
    results = axe.run()
    violations = results.get("violations", [])
    flattened = flatten_violations(violations)
    enriched = enrich_findings(flattened, guidance)

    # CSV
    df = pd.DataFrame(enriched)
    csv_file = os.path.join(output_dir, f"{url.replace('://','_').replace('/','_')}_enriched.csv")
    df.to_csv(csv_file, index=False)

    # Screenshot
    screenshot_file = os.path.join(output_dir, f"{url.replace('://','_').replace('/','_')}_screenshot.png")
    driver.save_screenshot(screenshot_file)

    # Lighthouse
    lh_file = os.path.join(output_dir, f"{url.replace('://','_').replace('/','_')}_lighthouse.json")
    lh_score = run_lighthouse(url, lh_file)

    # PDF
    pdf = AuditPDF()
    pdf.add_page()
    pdf.add_summary(url, total_violations=len(violations), lighthouse_score=lh_score)
    pdf.add_violation_table(enriched)
    pdf.add_screenshot(screenshot_file)
    pdf_file = os.path.join(output_dir, f"{url.replace('://','_').replace('/','_')}_audit.pdf")
    pdf.output(pdf_file)

    print(f"Completed scan for {url}. Report saved: {pdf_file}")

# ----------------------------
# Main Selenium Orchestrator
# ----------------------------
def main(urls):
    guidance = load_guidance("guidance.yaml")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"axe_scan_results_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    driver = webdriver.Chrome()
    for url in urls:
        try:
            scan_url(url, guidance, driver, output_dir)
        except Exception as e:
            print(f"Error scanning {url}: {e}")
    driver.quit()
    print("All Selenium scans completed successfully!")
