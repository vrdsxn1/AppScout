"""Manual claim-review helpers; retrieval quality remains separate from verdicts."""

from collections import Counter
from typing import Any

from appscout.models import AppResearchRecord

VERDICT_OPTIONS = {
    "supported",
    "partially_supported",
    "unsupported",
    "source_unavailable",
    "unclear",
}
INCONCLUSIVE_VERDICTS = {"partially_supported", "source_unavailable", "unclear"}


class WorksheetError(ValueError):
    """Invalid worksheet row or mismatch against the selected evidence."""


def validate_worksheet(records: list[dict[str, Any]], rows: list[dict[str, str]]) -> list[tuple[dict, dict]]:
    """Validate exact app/field/claim/URL matches without judging claim support."""
    by_app = {record["app_name"].casefold(): record for record in records}
    seen: set[tuple[str, str, str, str]] = set()
    matches: list[tuple[dict, dict]] = []
    required = (
        "app_name", "category", "field", "claim", "evidence_url", "source_title",
        "retrieved_excerpt", "retrieval_status", "evidence_quality",
        "claim_supported", "human_verdict", "reviewer_notes",
    )

    for line_number, row in enumerate(rows, start=2):
        missing = [column for column in required if column not in row]
        if missing:
            raise WorksheetError(f"Row {line_number}: missing columns: {', '.join(missing)}")
        key = (
            row["app_name"].strip().casefold(), row["field"].strip(),
            row["claim"], row["evidence_url"],
        )
        if key in seen:
            raise WorksheetError(f"Row {line_number}: duplicate review row")
        seen.add(key)
        record = by_app.get(key[0])
        if record is None:
            raise WorksheetError(f"Row {line_number}: app not found: {row['app_name']}")
        if row["category"] != record["category"]:
            raise WorksheetError(f"Row {line_number}: category does not match the record")
        evidence = next((item for item in record.get("evidence", [])
                         if item.get("field") == row["field"]
                         and item.get("claim") == row["claim"]
                         and str(item.get("url")) == row["evidence_url"]), None)
        if evidence is None:
            raise WorksheetError(f"Row {line_number}: no exact field/claim/URL evidence match")
        expected = {
            "source_title": evidence.get("source_title") or "",
            "retrieved_excerpt": evidence.get("excerpt") or "",
            "retrieval_status": evidence.get("retrieval_status") or "",
            "evidence_quality": evidence.get("evidence_quality") or "",
            "claim_supported": evidence.get("claim_supported") or "unverified",
        }
        for column, value in expected.items():
            if row[column] != str(value):
                raise WorksheetError(f"Row {line_number}: {column} was changed from the evidence record")
        verdict = row["human_verdict"].strip()
        if verdict and verdict not in VERDICT_OPTIONS:
            raise WorksheetError(f"Row {line_number}: invalid human_verdict {verdict!r}")
        matches.append((evidence, row))
    return matches


def summarize_verdicts(rows: list[dict[str, str]]) -> dict[str, int]:
    """Count human outcomes only; blank rows remain pending."""
    counts = Counter(row.get("human_verdict", "").strip() for row in rows)
    completed = sum(counts[verdict] for verdict in VERDICT_OPTIONS)
    return {
        "sample_size": len(rows),
        "completed": completed,
        "pending": counts[""],
        "supported": counts["supported"],
        "unsupported": counts["unsupported"],
        "inconclusive": sum(counts[v] for v in INCONCLUSIVE_VERDICTS),
        "partially_supported": counts["partially_supported"],
        "source_unavailable": counts["source_unavailable"],
        "unclear": counts["unclear"],
    }


def apply_human_verdicts(records: list[dict[str, Any]], matches: list[tuple[dict, dict]]) -> int:
    """Apply only nonblank human verdicts; preserve automated fields verbatim."""
    updated = 0
    for evidence, row in matches:
        verdict = row["human_verdict"].strip()
        if not verdict:
            continue
        existing = evidence.get("human_verdict")
        if existing and existing != verdict:
            raise WorksheetError(
                f"Conflicting human verdict for {row['app_name']} / {row['field']} / {row['evidence_url']}"
            )
        if evidence.get("claim_supported", "unverified") != row["claim_supported"]:
            raise WorksheetError("Automated claim_supported status changed; refusing to apply review")
        evidence["human_verdict"] = verdict
        evidence["review_method"] = "manual review via Scrape.do worksheet"
        updated += 1

    for record in records:
        AppResearchRecord.model_validate(record)
    return updated
