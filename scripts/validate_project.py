"""Validate all assignment records and preserve the original reviewed sample."""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from appscout.evidence_quality import classify_excerpt
from appscout.models import AppResearchRecord


def main() -> int:
    errors = []
    with (ROOT / "data" / "apps.csv").open("r", encoding="utf-8-sig", newline="") as file:
        apps = list(csv.DictReader(file))
    app_names = [x["app_name"].strip().casefold() for x in apps]
    if len(apps) != 100 or len(app_names) != len(set(app_names)):
        errors.append(f"Assignment list: expected 100 unique apps, found {len(apps)} rows/{len(set(app_names))} unique names")

    def read_records(filename):
        data = json.loads((ROOT / "output" / filename).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{filename} must be a JSON list")
        return data

    baseline = read_records("research_results_v2.json")
    full = read_records("research_results_free.json")
    if len(full) != 100:
        errors.append(f"Full-list output has {len(full)} records instead of 100")
    full_names = [x.get("app_name", "").strip().casefold() for x in full]
    if full_names != app_names:
        errors.append("Full-list output names/order do not exactly match data/apps.csv")
    for i, item in enumerate(full, 1):
        try:
            AppResearchRecord.model_validate(item)
        except Exception as exc:
            errors.append(f"Full record #{i} failed Pydantic validation: {exc}")

    by_full = {x["app_name"].casefold(): x for x in full}
    # Original 13 app evidence objects, including all 15 human-supported entries,
    # must remain identical inside the separate full-list output.
    for old in baseline:
        current = by_full.get(old["app_name"].casefold())
        if current is None or current.get("evidence") != old.get("evidence"):
            errors.append(f"Original evidence changed or missing for {old['app_name']}")

    with (ROOT / "output" / "manual_verification_sample.csv").open("r", encoding="utf-8-sig", newline="") as file:
        worksheet = list(csv.DictReader(file))
    reviewed = []
    for row in worksheet:
        record = by_full.get(row["app_name"].casefold())
        match = next((e for e in record.get("evidence", []) if e.get("claim") == row["claim"] and e.get("url") == row["evidence_url"]), None) if record else None
        if match is None or match.get("human_verdict") != "supported":
            errors.append(f"Human-supported sample not preserved for {row.get('app_name')}")
        reviewed.append(row)
    human_records = [e for r in full for e in r.get("evidence", []) if e.get("human_verdict") == "supported"]
    if len(reviewed) != 15 or len(human_records) != 15:
        errors.append(f"Expected 15 reviewed claims; worksheet={len(reviewed)}, full output={len(human_records)}")

    with (ROOT / "output" / "analysis.json").open("r", encoding="utf-8") as file:
        summary = json.load(file)
    usable_apps = sum(1 for r in full if any(e.get("excerpt") and e.get("retrieval_status") == "retrieved" and (e.get("evidence_quality") == "usable" or (not e.get("evidence_quality") and classify_excerpt(e["excerpt"])[0] == "usable")) for e in r.get("evidence", [])))
    if summary.get("apps_with_usable_evidence") != usable_apps:
        errors.append(f"Analysis usable-evidence count mismatch: expected {usable_apps}, got {summary.get('apps_with_usable_evidence')}")

    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(f"PASS: {len(apps)} assignment names match {len(full)} Pydantic-valid full-list records in order.")
    print(f"PASS: original {len(baseline)} complete records preserved; {len(human_records)} human-supported entries retained.")
    print(f"PASS: {usable_apps} apps have at least one readable retrieved excerpt (readability only; not verification).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
