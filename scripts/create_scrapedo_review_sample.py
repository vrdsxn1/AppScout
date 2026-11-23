"""Create a separate human-review worksheet from new Scrape.do evidence.

Local file processing only. This script never makes network requests.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCE = ROOT / "output" / "research_results_scrapedo.json"
BASELINE = ROOT / "output" / "research_results_free.json"
WORKSHEET = ROOT / "output" / "scrapedo_manual_verification_sample.csv"

# Fixed, reviewable selection: broad category coverage, multiple fields, and a
# mixture of clear prose and borderline excerpts for a useful human audit.
SELECTION = [
    ("Pumble", "access_model"),
    ("Telegram", "blockers"),
    ("Google Ads", "mcp_status"),
    ("Klaviyo", "auth_methods"),
    ("Klaviyo", "blockers"),
    ("Shopify", "auth_methods"),
    ("BigCommerce", "api_type"),
    ("Magento (Adobe Commerce)", "api_type"),
    ("Apify", "auth_methods"),
    ("Apify", "blockers"),
    ("Firecrawl", "auth_methods"),
    ("Netlify", "auth_methods"),
    ("Cloudflare", "auth_methods"),
    ("Sentry", "auth_methods"),
    ("Coda", "mcp_status"),
    ("Coda", "auth_methods"),
    ("Monday.com", "blockers"),
    ("Plaid", "mcp_status"),
    ("Devin", "access_model"),
    ("Grain", "access_model"),
]

COLUMNS = [
    "app_name", "category", "field", "claim", "evidence_url", "source_title",
    "retrieved_excerpt", "retrieval_status", "evidence_quality",
    "evidence_quality_note", "claim_supported", "human_verdict", "reviewer_notes",
]


def main() -> None:
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    old_keys = {
        (record["app_name"].casefold(), evidence.get("field"), evidence["claim"], str(evidence["url"]))
        for record in baseline for evidence in record.get("evidence", [])
    }
    by_app = {record["app_name"]: record for record in records}
    rows = []

    for app_name, field in SELECTION:
        record = by_app[app_name]
        candidates = [
            evidence for evidence in record.get("evidence", [])
            if evidence.get("field") == field
            and (record["app_name"].casefold(), evidence.get("field"), evidence["claim"], str(evidence["url"])) not in old_keys
            and evidence.get("retrieval_status") == "retrieved"
            and evidence.get("evidence_quality") == "usable"
            and evidence.get("claim_supported", "unverified") == "unverified"
            and not evidence.get("human_verdict")
            and str(evidence.get("url", "")).startswith(("http://", "https://"))
            and evidence.get("excerpt")
        ]
        if not candidates:
            raise ValueError(f"No eligible new evidence for {app_name} / {field}")
        evidence = candidates[0]
        rows.append({
            "app_name": record["app_name"],
            "category": record["category"],
            "field": field,
            "claim": evidence["claim"],
            "evidence_url": str(evidence["url"]),
            "source_title": evidence.get("source_title") or "",
            "retrieved_excerpt": evidence.get("excerpt") or "",
            "retrieval_status": evidence.get("retrieval_status") or "",
            "evidence_quality": evidence.get("evidence_quality") or "",
            "evidence_quality_note": evidence.get("evidence_quality_note") or "",
            "claim_supported": evidence.get("claim_supported") or "unverified",
            "human_verdict": "",
            "reviewer_notes": "",
        })

    WORKSHEET.parent.mkdir(parents=True, exist_ok=True)
    with WORKSHEET.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created {WORKSHEET.relative_to(ROOT)} with {len(rows)} blank review rows across {len({r['category'] for r in rows})} categories.")


if __name__ == "__main__":
    main()
