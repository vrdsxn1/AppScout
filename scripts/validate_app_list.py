"""Check that data/apps.csv contains the complete assignment app list shape."""

import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "apps.csv"
ASSIGNMENT_URL = (
    "https://composio.notion.site/AI-Product-Ops-Intern-The-take-home-assignment-"
    "391f261a6dfe80e9946bee899d3a3762"
)
EXPECTED_COLUMNS = ["app_name", "category", "source_url"]


def validate_app_list() -> list[str]:
    errors: list[str] = []

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != EXPECTED_COLUMNS:
            return [f"Expected columns {EXPECTED_COLUMNS}, found {reader.fieldnames}."]
        rows = list(reader)

    if len(rows) != 100:
        errors.append(f"Expected exactly 100 app rows; found {len(rows)}.")

    names = [row["app_name"].strip() for row in rows]
    if any(not name for name in names):
        errors.append("One or more app names are blank.")
    nonblank_names = [name.casefold() for name in names if name]
    if len(nonblank_names) != len(set(nonblank_names)):
        errors.append("App names are not unique (case-insensitive check).")

    if any(not row["category"].strip() for row in rows):
        errors.append("One or more categories are blank.")
    if any(row["source_url"].strip() != ASSIGNMENT_URL for row in rows):
        errors.append("One or more rows do not have the exact assignment source URL.")

    return errors


if __name__ == "__main__":
    validation_errors = validate_app_list()
    if validation_errors:
        for error in validation_errors:
            print(f"FAIL: {error}")
        sys.exit(1)

    print("PASS: 100 app rows; names are nonblank and unique; categories are nonblank;")
    print("      every row contains the exact assignment source URL.")
