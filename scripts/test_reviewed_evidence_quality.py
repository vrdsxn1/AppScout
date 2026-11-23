"""Regression tests against the imported 20-claim human-review sample.

These tests inspect stored local data only and make no network requests.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from appscout.evidence_quality import classify_excerpt


def main() -> int:
    records = json.loads((ROOT / "output" / "research_results_scrapedo.json").read_text(encoding="utf-8"))
    by_app = {record["app_name"].casefold(): record for record in records}
    with (ROOT / "output" / "scrapedo_manual_verification_import_ready.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    expected = {
        ("Pumble", "access_model"): "page_shell",
        ("BigCommerce", "api_type"): "page_shell",
        ("Magento (Adobe Commerce)", "api_type"): "page_shell",
        ("Devin", "access_model"): "page_shell",
        ("Grain", "access_model"): "page_shell",
        ("Google Ads", "mcp_status"): "navigation",
        ("Apify", "blockers"): "insufficient",
        # Plaid's excerpt is readable, but the human reviewer found its
        # relationship to MCP unclear. Readability alone should remain usable.
        ("Plaid", "mcp_status"): "usable",
    }
    checked = 0
    for (app_name, field), expected_quality in expected.items():
        row = next(row for row in rows if row["app_name"] == app_name and row["field"] == field)
        record = by_app[app_name.casefold()]
        evidence = next(
            item for item in record["evidence"]
            if item.get("field") == row["field"]
            and item.get("claim") == row["claim"]
            and str(item.get("url")) == row["evidence_url"]
        )
        before = (evidence.get("claim_supported"), evidence.get("human_verdict"))
        quality, reason = classify_excerpt(evidence.get("excerpt"))
        assert quality == expected_quality, f"{app_name}: expected {expected_quality}, got {quality}: {reason}"
        after = (evidence.get("claim_supported"), evidence.get("human_verdict"))
        assert after == before, f"{app_name}: readability classification changed claim/human status"
        print(f"PASS {app_name} / {field}: {quality} — {reason}")
        checked += 1

    assert len(rows) == 20
    assert sum(bool(row["human_verdict"]) for row in rows) == 20
    print(f"PASS reviewed sample intact: {checked} classifier cases; all 20 verdicts remain present.")
    print("No claim was automatically marked supported; no network requests made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
