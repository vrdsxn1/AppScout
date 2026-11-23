"""Validate and optionally import human verdicts from the Scrape.do sample.

Local-only utility: it reads JSON/CSV and never accesses the network. Without
--apply it is a read-only dry run. --apply changes only matched human_verdict
and review_method fields in research_results_scrapedo.json.
"""

import argparse
import csv
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from appscout.models import AppResearchRecord
from appscout.verification import apply_human_verdicts, summarize_verdicts, validate_worksheet

DEFAULT_DATA = ROOT / "output" / "research_results_scrapedo.json"
# The reviewer-owned CSV is preserved byte-for-byte. The import-ready copy is
# used by default because it records the explicit typo/excerpt normalization.
DEFAULT_WORKSHEET = ROOT / "output" / "scrapedo_manual_verification_import_ready.csv"


def read_inputs(data_path: Path, worksheet_path: Path):
    # Validate with Pydantic but keep the original dictionaries intact so an
    # apply operation cannot normalize URLs, add defaults, or discard fields.
    records = json.loads(data_path.read_text(encoding="utf-8"))
    for record in records:
        AppResearchRecord.model_validate(record)
    with worksheet_path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    matches = validate_worksheet(records, rows)
    return records, rows, matches


def print_summary(records, rows, matches, applied: int = 0) -> None:
    counts = summarize_verdicts(rows)
    automated = Counter(row["claim_supported"] for row in rows)
    qualities = Counter(row["evidence_quality"] for row in rows)
    apps = sorted({row["app_name"] for row in rows})
    print(f"Worksheet claims: {counts['sample_size']}")
    print(f"Exact evidence matches: {len(matches)}")
    print(f"Human reviews completed: {counts['completed']}; pending: {counts['pending']}")
    print(f"Human supported: {counts['supported']}; unsupported: {counts['unsupported']}; inconclusive: {counts['inconclusive']}")
    print("Inconclusive detail: " + ", ".join(
        f"{label}={counts[key]}" for label, key in (
            ("partially_supported", "partially_supported"),
            ("source_unavailable", "source_unavailable"),
            ("unclear", "unclear"),
        )
    ))
    print("Automated claim_supported statuses: " + ", ".join(f"{k}={v}" for k, v in sorted(automated.items())))
    print("Automated evidence quality flags: " + ", ".join(f"{k}={v}" for k, v in sorted(qualities.items())))
    print(f"Apps represented: {', '.join(apps)}")
    if applied:
        print(f"Human verdicts applied: {applied} (automated statuses preserved)")
    print("This is a manually reviewed sample summary; it is not overall accuracy.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--worksheet", type=Path, default=DEFAULT_WORKSHEET)
    parser.add_argument("--apply", action="store_true", help="write nonblank human verdicts to the matching Scrape.do data records")
    args = parser.parse_args()
    try:
        records, rows, matches = read_inputs(args.data, args.worksheet)
        applied = 0
        if args.apply:
            applied = apply_human_verdicts(records, matches)
            # Validate and serialize to a temporary sibling, then replace atomically.
            for record in records:
                AppResearchRecord.model_validate(record)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=args.data.parent, delete=False) as handle:
                temp_path = Path(handle.name)
                json.dump(records, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            temp_path.replace(args.data)
        print_summary(records, rows, matches, applied)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Verification input error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
