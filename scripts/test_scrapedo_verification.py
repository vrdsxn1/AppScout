"""Local tests for worksheet matching and human verdict ingestion; no network."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from appscout.models import AppResearchRecord
from appscout.verification import (
    WorksheetError,
    apply_human_verdicts,
    summarize_verdicts,
    validate_worksheet,
)


def fixture():
    evidence = {
        "claim": "The API accepts bearer tokens.", "field": "auth_methods",
        "url": "https://docs.example.test/auth", "source_type": "docs",
        "source_title": "Authentication", "excerpt": "Use bearer tokens for API requests.",
        "retrieval_status": "retrieved", "claim_supported": "unverified",
        "evidence_quality": "usable", "evidence_quality_note": "Readable prose.",
    }
    record = {
        "app_name": "Example App", "category": "Developer Tools",
        "description": "An example application.", "auth_methods": ["unknown"],
        "access_model": "unknown", "api_type": "REST", "api_breadth": "unknown",
        "mcp_status": "unknown", "buildability": "unclear", "blockers": [],
        "evidence": [evidence], "confidence": "low", "last_checked": "2026-11-23",
    }
    row = {
        "app_name": record["app_name"], "category": record["category"],
        "field": evidence["field"], "claim": evidence["claim"],
        "evidence_url": evidence["url"], "source_title": evidence["source_title"],
        "retrieved_excerpt": evidence["excerpt"], "retrieval_status": evidence["retrieval_status"],
        "evidence_quality": evidence["evidence_quality"],
        "evidence_quality_note": evidence["evidence_quality_note"],
        "claim_supported": evidence["claim_supported"], "human_verdict": "",
        "reviewer_notes": "",
    }
    return [record], [row]


class VerificationWorkflowTests(unittest.TestCase):
    def test_exact_match_and_blank_row(self):
        records, rows = fixture()
        matches = validate_worksheet(records, rows)
        self.assertEqual(len(matches), 1)
        self.assertEqual(summarize_verdicts(rows)["pending"], 1)
        self.assertEqual(rows[0]["human_verdict"], "")

    def test_verdict_counts_and_automated_fields_preserved(self):
        records, rows = fixture()
        verdicts = ["supported", "unsupported", "partially_supported", "source_unavailable", "unclear"]
        all_rows, all_matches = [], []
        all_records = []
        for i, verdict in enumerate(verdicts):
            recs, sample = fixture()
            recs[0]["app_name"] += str(i)
            sample[0]["app_name"] += str(i)
            sample[0]["human_verdict"] = verdict
            all_records.extend(recs)
            all_rows.extend(sample)
            all_matches.extend(validate_worksheet(recs, sample))
        applied = apply_human_verdicts(all_records, all_matches)
        counts = summarize_verdicts(all_rows)
        self.assertEqual(applied, 5)
        self.assertEqual((counts["supported"], counts["unsupported"], counts["inconclusive"]), (1, 1, 3))
        for record in all_records:
            item = record["evidence"][0]
            self.assertEqual(item["claim_supported"], "unverified")
            self.assertEqual(item["evidence_quality"], "usable")
            self.assertIsNotNone(item["human_verdict"])
        for record in all_records:
            AppResearchRecord.model_validate(record)

    def test_rejects_mismatched_excerpt_or_invalid_verdict(self):
        records, rows = fixture()
        rows[0]["retrieved_excerpt"] = "edited excerpt"
        with self.assertRaises(WorksheetError):
            validate_worksheet(records, rows)
        records, rows = fixture()
        rows[0]["human_verdict"] = "verified"
        with self.assertRaises(WorksheetError):
            validate_worksheet(records, rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
