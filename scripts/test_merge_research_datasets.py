"""Local merge invariants; no web requests or production-file writes."""

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.merge_research_datasets import merge_records


def evidence(claim, excerpt, *, field="api_type", human_verdict=None, quality="usable"):
    return {
        "field": field, "claim": claim, "url": "https://docs.example.test/api",
        "excerpt": excerpt, "source_type": "official docs", "source_title": "API docs",
        "retrieval_status": "retrieved", "claim_supported": "unverified",
        "evidence_quality": quality, "human_verdict": human_verdict,
        "review_method": "human review" if human_verdict else None,
    }


def record(evidence_rows, *, status="blocked", api_type="unknown"):
    return {
        "app_name": "Example", "category": "Developer Tools", "description": "Example.",
        "auth_methods": [], "access_model": "unknown", "api_type": api_type,
        "api_breadth": "unknown", "mcp_status": "unknown", "buildability": "unclear",
        "blockers": [], "evidence": deepcopy(evidence_rows), "confidence": "low",
        "last_checked": "2026-11-23", "research_status": status, "research_note": None,
        "source_attempts": [{"url": "https://docs.example.test/api", "status": "blocked_robots", "note": "base"}],
        "source_queue": ["https://docs.example.test/api"],
    }


class MergeTests(unittest.TestCase):
    def test_exact_identity_only_and_manual_metadata_preserved(self):
        base_evidence = evidence("REST API exists.", "The REST API provides records.")
        original = record([base_evidence])
        duplicate = evidence("REST API exists.", "The REST API provides records.", human_verdict="supported", quality="page_shell")
        same_url_distinct_claim = evidence("The API has list endpoints.", "The REST API provides records.")
        same_claim_distinct_excerpt = evidence("REST API exists.", "REST requests return records and metadata.")
        scrapedo = record([duplicate, same_url_distinct_claim, same_claim_distinct_excerpt], status="partial", api_type="REST")
        scrapedo["source_attempts"].append({"url": "https://docs.example.test/api", "status": "retrieved", "note": "scrape"})
        scrapedo["source_queue"].append("https://docs.example.test/pricing")
        review = [{
            "app_name": "Example", "field": "api_type", "claim": "REST API exists.",
            "evidence_url": "https://docs.example.test/api", "retrieved_excerpt": "The REST API provides records.",
            "human_verdict": "supported",
            "reviewer_notes": "checked full page",
        }]

        merged, audit, totals = merge_records([original], [scrapedo], review)
        result = merged[0]
        self.assertEqual(len(result["evidence"]), 3)
        first = result["evidence"][0]
        self.assertEqual(first["human_verdict"], "supported")
        self.assertEqual(first["reviewer_notes"], "checked full page")
        self.assertEqual(first["claim_supported"], "unverified")
        self.assertEqual(first["evidence_quality"], "usable")
        self.assertEqual(result["api_type"], "unknown")
        self.assertEqual(result["research_status"], "blocked")
        self.assertEqual({x["status"] for x in result["source_attempts"]}, {"blocked_robots", "retrieved"})
        self.assertEqual(result["source_queue"], ["https://docs.example.test/api", "https://docs.example.test/pricing"])
        self.assertEqual(totals["evidence_added"], 2)
        self.assertEqual(totals["evidence_deduplicated"], 1)
        self.assertEqual(totals["human_reviews_carried"], 1)
        self.assertEqual(audit[0]["field_conflicts"], ["api_type", "research_status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
