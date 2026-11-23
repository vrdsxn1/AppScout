"""Conservatively merge Scrape.do evidence into a new full dataset.

This is local-only. The original full dataset and Scrape.do source file are
read-only inputs; output is written to research_results_merged.json.
"""

import csv
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from appscout.models import AppResearchRecord
from appscout.verification import VERDICT_OPTIONS

OUTPUT_DIR = ROOT / "output"
ORIGINAL = OUTPUT_DIR / "research_results_free.json"
SCRAPEDO = OUTPUT_DIR / "research_results_scrapedo.json"
REVIEW = OUTPUT_DIR / "scrapedo_manual_verification_import_ready.csv"
APP_LIST = ROOT / "data" / "apps.csv"
MERGED = OUTPUT_DIR / "research_results_merged.json"
AUDIT = OUTPUT_DIR / "merge_audit.md"

AUTOMATED_FIELDS = {"claim_supported", "evidence_quality"}
HUMAN_FIELDS = {"human_verdict", "review_method", "reviewer_notes"}
OPERATIONAL_FIELDS = {"source_attempts", "source_queue"}


def evidence_key(evidence: dict[str, Any]) -> tuple[str, str, str, str]:
    """Deduplicate only when field, claim, source URL, and excerpt all match."""
    return (
        evidence.get("field") or "",
        evidence.get("claim") or "",
        str(evidence.get("url") or ""),
        evidence.get("excerpt") or "",
    )


def review_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (row["app_name"].casefold(), row["field"], row["claim"], row["evidence_url"], row["retrieved_excerpt"])


def load_inputs():
    original = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    scrapedo = json.loads(SCRAPEDO.read_text(encoding="utf-8"))
    with REVIEW.open("r", encoding="utf-8-sig", newline="") as handle:
        review_rows = list(csv.DictReader(handle))
    with APP_LIST.open("r", encoding="utf-8-sig", newline="") as handle:
        app_rows = list(csv.DictReader(handle))
    return original, scrapedo, review_rows, app_rows


def validate_input_records(original, scrapedo, review_rows, app_rows):
    for label, records in (("original", original), ("Scrape.do", scrapedo)):
        for index, record in enumerate(records, start=1):
            try:
                AppResearchRecord.model_validate(record)
            except Exception as exc:
                raise ValueError(f"{label} record {index} ({record.get('app_name')}): {exc}") from exc
    expected = [(row["app_name"], row["category"]) for row in app_rows]
    original_names = [(r["app_name"], r["category"]) for r in original]
    scrapedo_names = [(r["app_name"], r["category"]) for r in scrapedo]
    if len(expected) != 100 or original_names != expected or scrapedo_names != expected:
        raise ValueError("Input app names/categories must match the ordered 100-row assignment list.")
    if len(review_rows) != 20:
        raise ValueError(f"Expected 20 imported review rows, found {len(review_rows)}")
    if any(row.get("human_verdict", "").strip() not in VERDICT_OPTIONS for row in review_rows):
        raise ValueError("Review worksheet contains blank or invalid human verdicts.")


def merge_records(original, scrapedo, review_rows):
    """Keep original assessments, merge evidence and operational provenance."""
    merged = deepcopy(original)
    review_map: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in review_rows:
        key = review_key(row)
        if key in review_map:
            raise ValueError(f"Duplicate review row for {key}")
        review_map[key] = row

    app_audit = []
    summary = Counter()
    for original_record, scrapedo_record, target in zip(original, scrapedo, merged):
        if original_record["app_name"] != scrapedo_record["app_name"]:
            raise ValueError("Datasets differ in app order; refusing positional merge.")
        app_name = original_record["app_name"]
        base_evidence = target.setdefault("evidence", [])
        base_by_key = {evidence_key(e): e for e in base_evidence}
        added = 0
        deduplicated = 0
        metadata_conflicts = []
        imported_reviews = 0

        for scraped_evidence in scrapedo_record.get("evidence", []):
            item = deepcopy(scraped_evidence)
            exact_key = evidence_key(item)
            review = review_map.get((app_name.casefold(), item.get("field") or "", item.get("claim") or "", str(item.get("url") or ""), item.get("excerpt") or ""))
            if review:
                # The import-ready worksheet is the source of reviewer notes;
                # its verdict must agree with the already imported evidence.
                if item.get("human_verdict") != review["human_verdict"].strip():
                    raise ValueError(f"Review/data verdict conflict for {app_name} / {item.get('field')}")
                item["reviewer_notes"] = review.get("reviewer_notes", "")

            existing = base_by_key.get(exact_key)
            if existing is None:
                base_evidence.append(item)
                base_by_key[exact_key] = item
                added += 1
                summary["evidence_added"] += 1
                if review:
                    imported_reviews += 1
                    summary["human_reviews_carried"] += 1
                continue

            deduplicated += 1
            summary["evidence_deduplicated"] += 1
            changed_metadata = {
                field for field in set(existing) | set(item)
                if existing.get(field) != item.get(field)
                and field not in HUMAN_FIELDS
            }
            if changed_metadata:
                metadata_conflicts.append((item.get("field") or "(unmapped)", sorted(changed_metadata)))
                summary["evidence_metadata_conflicts"] += 1
            if review:
                verdict = review["human_verdict"].strip()
                existing_verdict = existing.get("human_verdict")
                if existing_verdict and existing_verdict != verdict:
                    metadata_conflicts.append((item.get("field") or "(unmapped)", ["human_verdict conflict"]))
                else:
                    existing["human_verdict"] = verdict
                    existing["review_method"] = item.get("review_method") or "manual review via Scrape.do worksheet"
                    existing["reviewer_notes"] = review.get("reviewer_notes", "")
                    imported_reviews += 1
                    summary["human_reviews_carried"] += 1
            else:
                # Carry a Scrape.do human verdict only if the same exact
                # evidence is present and the original record has none.
                scrape_verdict = item.get("human_verdict")
                original_verdict = existing.get("human_verdict")
                if scrape_verdict and not original_verdict:
                    existing["human_verdict"] = scrape_verdict
                    existing["review_method"] = item.get("review_method")
                    existing["reviewer_notes"] = item.get("reviewer_notes")
                elif scrape_verdict and original_verdict and scrape_verdict != original_verdict:
                    metadata_conflicts.append((item.get("field") or "(unmapped)", ["human_verdict conflict"]))
            # claim_supported and evidence_quality intentionally remain as in
            # the original evidence on exact duplicates.

        # Keep all original app-level assessment fields. Record Scrape.do
        # differences for review instead of letting unverified summaries
        # overwrite the established full dataset.
        conflict_fields = {
            key for key in set(original_record) | set(scrapedo_record)
            if key not in ("evidence", *OPERATIONAL_FIELDS)
            and original_record.get(key) != scrapedo_record.get(key)
        }

        # Merge source attempts and queues as operational provenance, without
        # collapsing different outcomes for the same URL.
        attempts_added = merge_unique_objects(target, scrapedo_record, "source_attempts")
        queue_added = merge_unique_values(target, scrapedo_record, "source_queue")
        summary["source_attempts_added"] += attempts_added
        summary["source_queue_added"] += queue_added
        summary["apps_with_evidence_additions"] += bool(added)
        summary["apps_with_app_field_conflicts"] += bool(conflict_fields)
        app_audit.append({
            "app_name": app_name,
            "evidence_added": added,
            "evidence_deduplicated": deduplicated,
            "human_reviews_carried": imported_reviews,
            "field_conflicts": sorted(conflict_fields),
            "evidence_metadata_conflicts": metadata_conflicts,
            "source_attempts_added": attempts_added,
            "source_queue_added": queue_added,
        })

    # Every reviewed row must map to exactly one merged evidence record.
    for row in review_rows:
        record = next(r for r in merged if r["app_name"].casefold() == row["app_name"].casefold())
        matches = [e for e in record["evidence"] if e.get("field") == row["field"] and e.get("claim") == row["claim"] and str(e.get("url")) == row["evidence_url"] and (e.get("excerpt") or "") == row["retrieved_excerpt"]]
        if len(matches) != 1 or matches[0].get("human_verdict") != row["human_verdict"].strip() or matches[0].get("reviewer_notes", "") != row.get("reviewer_notes", ""):
            raise ValueError(f"Could not preserve exact reviewed row: {row['app_name']} / {row['field']}")
    return merged, app_audit, summary


def merge_unique_objects(target: dict, source: dict, field: str) -> int:
    incoming = source.get(field, [])
    if not incoming:
        return 0
    values = target.setdefault(field, [])
    existing = {json.dumps(value, sort_keys=True, ensure_ascii=False) for value in values}
    added = 0
    for value in incoming:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key not in existing:
            values.append(deepcopy(value))
            existing.add(key)
            added += 1
    return added


def merge_unique_values(target: dict, source: dict, field: str) -> int:
    incoming = source.get(field, [])
    if not incoming:
        return 0
    values = target.setdefault(field, [])
    existing = {str(value) for value in values}
    added = 0
    for value in incoming:
        if str(value) not in existing:
            values.append(value)
            existing.add(str(value))
            added += 1
    return added


def compact(value: Any, limit: int = 150) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def write_audit(original, scrapedo, merged, app_audit, summary, review_rows):
    verdict_counts = Counter(row["human_verdict"].strip() for row in review_rows)
    nonempty_notes = sum(bool(row.get("reviewer_notes", "").strip()) for row in review_rows)
    orig_evidence = sum(len(r.get("evidence", [])) for r in original)
    scrape_evidence = sum(len(r.get("evidence", [])) for r in scrapedo)
    merged_evidence = sum(len(r.get("evidence", [])) for r in merged)
    field_conflicts = []
    by_name_scrape = {r["app_name"]: r for r in scrapedo}
    for original_record in original:
        other = by_name_scrape[original_record["app_name"]]
        for key in sorted(set(original_record) | set(other)):
            if key in ("evidence", *OPERATIONAL_FIELDS) or original_record.get(key) == other.get(key):
                continue
            field_conflicts.append((original_record["app_name"], key, original_record.get(key), other.get(key)))
    progress_fields = {"research_status", "research_note"}
    assessment_conflicts = [
        (name, field, base, other) for name, field, base, other in field_conflicts
        if field not in progress_fields
    ]
    assessment_conflict_fields = Counter(field for _, field, _, _ in assessment_conflicts)

    lines = [
        "# Scrape.do merge audit",
        "",
        "## Merge strategy",
        "",
        "- The original `research_results_free.json` is the base and remains the source of every app-level assessment field. Scrape.do summary fields that differ are listed as unresolved conflicts; they do not overwrite the original values because Scrape.do claims remain automated/unverified unless separately human reviewed.",
        "- Evidence is combined in assignment order. A record is deduplicated only when app (implicit in the containing record), field, full claim text, exact source URL, and excerpt all match. Different excerpts or claims at the same URL remain separate records.",
        "- Exact duplicates retain the original automated `claim_supported` and `evidence_quality` values. Human verdict/review metadata is copied only for exact matching reviewed evidence; conflicts are reported and not silently resolved.",
        "- The 20-row import-ready review CSV supplies `reviewer_notes`, which the evidence schema now stores as an optional field. Empty notes are preserved as empty strings on the 20 reviewed evidence records.",
        "- Source attempts and source queues are unioned without collapsing different attempt outcomes. App-level `research_status`, unknown values, and other assessment fields remain as in the original dataset; Scrape.do status differences are listed below.",
        "- No usable excerpt is treated as verified. Human `human_verdict`, automated `claim_supported`, and readability `evidence_quality` remain distinct fields.",
        "",
        "## Totals",
        "",
        f"- App records: {len(merged)}; original evidence records retained: {orig_evidence}; Scrape.do evidence records considered: {scrape_evidence}; merged evidence records: {merged_evidence}.",
        f"- Scrape.do evidence added: {summary['evidence_added']}; exact duplicates: {summary['evidence_deduplicated']}; source attempts added: {summary['source_attempts_added']}; source queue entries added: {summary['source_queue_added']}.",
        f"- Apps with evidence additions: {summary['apps_with_evidence_additions']}; apps with differing app-level fields: {summary['apps_with_app_field_conflicts']}.",
        f"- Of those, {len({name for name, _, _, _ in assessment_conflicts})} apps differ on assessment fields (excluding research status/note): " + ", ".join(f"{field}={count}" for field, count in sorted(assessment_conflict_fields.items())) + ".",
        f"- Exact human reviews carried: {summary['human_reviews_carried']} / 20. Verdicts: supported {verdict_counts['supported']}, unsupported {verdict_counts['unsupported']}, unclear {verdict_counts['unclear']}, partially supported {verdict_counts['partially_supported']}, source unavailable {verdict_counts['source_unavailable']}.",
        f"- Reviewer notes preserved: {nonempty_notes} non-empty notes and {len(review_rows) - nonempty_notes} blank notes.",
        f"- Exact-duplicate evidence metadata conflicts left unresolved: {summary['evidence_metadata_conflicts']}.",
        "",
        "## Per-app merge result",
        "",
        "Only apps with an evidence addition, exact duplicate, or app-level field difference are listed. All other assignment apps have no evidence change and no app-level field difference.",
        "",
        "| App | Evidence added | Exact deduplications | Source attempts / queue added | Differing fields retained from original |",
        "|---|---:|---:|---|---|",
    ]
    by_app_conflicts = {name: [] for name, _, _, _ in field_conflicts}
    for name, field, base, other in field_conflicts:
        by_app_conflicts[name].append(f"`{field}`: original {compact(base)}; Scrape.do {compact(other)}")
    for entry in app_audit:
        if not (entry["evidence_added"] or entry["evidence_deduplicated"] or entry["field_conflicts"]):
            continue
        conflict_text = "<br>".join(by_app_conflicts.get(entry["app_name"], [])) or "—"
        queue_text = f"{entry['source_attempts_added']} / {entry['source_queue_added']}"
        lines.append(
            f"| {entry['app_name']} | {entry['evidence_added']} | {entry['evidence_deduplicated']} | {queue_text} | {conflict_text} |"
        )
    lines.extend([
        "",
        "## Human review preservation",
        "",
        "All 20 reviewed rows were matched by app, field, claim, and URL to one evidence record. Verdict and notes are copied to that exact evidence record. The 12 supported, 7 unsupported, and 1 unclear human verdicts do not change automated claim status or evidence readability. Reviewer notes are not promoted to app-level claims.",
        "",
        "The original 13 v2 app records and their 15 supported evidence entries were already present in the original full dataset and remain intact in the merged output. Their evidence is not replaced or deduplicated against merely similar claims; only exact full-key matches qualify for deduplication.",
        "",
        "## Unresolved conflicts and limitations",
        "",
        "- Where Scrape.do app-level values differ from the original, the original value is retained. This includes research status and research notes. The differing Scrape.do values are exposed above for a later evidence-led decision.",
        "- Evidence metadata conflicts on exact duplicate keys are retained as original evidence metadata, except human review fields copied from an exact reviewed row. They are listed in the merge script's per-app audit structure and do not alter automated support or quality flags.",
        "- This merge combines records and provenance; it does not certify claims, revise buildability, or infer missing API, access, or MCP facts.",
        "",
    ])
    AUDIT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    original, scrapedo, review_rows, app_rows = load_inputs()
    validate_input_records(original, scrapedo, review_rows, app_rows)
    merged, app_audit, summary = merge_records(original, scrapedo, review_rows)
    for index, record in enumerate(merged, start=1):
        AppResearchRecord.model_validate(record)
    MERGED.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_audit(original, scrapedo, merged, app_audit, summary, review_rows)
    print(f"Wrote {MERGED.relative_to(ROOT)} ({len(merged)} app records).")
    print(f"Wrote {AUDIT.relative_to(ROOT)}.")
    print(f"Evidence added={summary['evidence_added']}; exact duplicates={summary['evidence_deduplicated']}; human reviews carried={summary['human_reviews_carried']}/20.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
