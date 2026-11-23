"""Local, evidence-aware summaries for AppScout's assignment and research."""

from collections import Counter
import re
from typing import Any

from appscout.evidence_quality import classify_excerpt


def contains_unknown(value: Any) -> bool:
    """Return whether a scalar/list visibly says that its value is uncertain."""
    values = value if isinstance(value, list) else [value]
    return any(
        re.search(r"\b(unknown|unclear|not established|not determined|unable to determine)\b", str(item), re.I)
        for item in values
    )


def api_bucket(value: str) -> str:
    text = value.strip().lower()
    if contains_unknown(text):
        return "Unknown / unclear"
    if text == "both" or "rest and graphql" in text or "rest + graphql" in text:
        return "REST + GraphQL"
    has_rest = "rest" in text
    has_graphql = "graphql" in text
    if has_rest and has_graphql:
        return "REST + GraphQL"
    if has_rest:
        return "REST"
    if has_graphql:
        return "GraphQL"
    return "Other / unspecified"


def access_flags(value: str) -> list[str]:
    """Non-exclusive access characteristics inferred from stored wording."""
    text = value.lower()
    flags: list[str] = []
    if contains_unknown(value):
        flags.append("Unknown / unclear")
    if any(term in text for term in ("self-serve", "self serve", "free", "trial")):
        flags.append("Self-serve, free, or trial mentioned")
    if any(term in text for term in ("paid", "pricing", "subscription", "per user", "per-agent", "plan-based")):
        flags.append("Paid plan or subscription mentioned")
    if any(term in text for term in ("admin", "administrator", "permission", "approval")):
        flags.append("Admin or permission gate mentioned")
    if any(term in text for term in ("contact sales", "contact-sales", "partnership", "outreach", "account manager")):
        flags.append("Outreach or account-manager gate mentioned")
    return flags or ["Not categorized"]


def auth_families(methods: list[str]) -> list[str]:
    text = " ".join(methods).lower()
    families = []
    if "oauth" in text:
        families.append("OAuth")
    if any(term in text for term in ("api key", "api token", "access token", "bearer token")):
        families.append("API/access token")
    if any(term in text for term in ("basic auth", "http basic", "basic authentication")):
        families.append("HTTP Basic")
    if not families and methods:
        families.append("Other documented method")
    return families


def blocker_topics(records: list[dict[str, Any]]) -> Counter[str]:
    patterns = {
        "Plan, edition, or paid add-on": r"plan|edition|license|paid|add-on|subscription|tier",
        "Permissions, scopes, or admin setup": r"permission|scope|administrator|admin|role|approval|authorize",
        "Rate limits or quotas": r"rate.limit|quota|daily allocation|credits|per minute|per second|per 24.hour",
        "Tenant/account setup": r"account|workspace|org|tenant|API key|client credentials|OAuth app",
        "Outreach or external approval": r"contact sales|contact support|account manager|partnership|outreach|written consent",
        "MCP eligibility or setup": r"MCP|AI client|OAuth client|endpoint",
    }
    counts: Counter[str] = Counter()
    for record in records:
        text = " ".join(record.get("blockers", [])) + " " + record.get("access_model", "")
        for label, pattern in patterns.items():
            if re.search(pattern, text, re.I):
                counts[label] += 1
    return counts


def analyze(records: list[dict[str, Any]], app_rows: list[dict[str, str]]) -> dict[str, Any]:
    """Summarize records without treating evidence retrieval as verification."""
    record_by_name = {row["app_name"].strip().casefold(): row for row in records}
    researched_names = {
        name for name, record in record_by_name.items()
        if record.get("research_status", "researched" if record.get("evidence") else "not_researched") in {"researched", "partial"}
    }
    categories = Counter(row["category"].strip() for row in app_rows)
    coverage = []
    for category, total in categories.items():
        researched = sum(
            1 for row in app_rows
            if row["category"].strip() == category and row["app_name"].strip().casefold() in researched_names
        )
        coverage.append({"category": category, "total": total, "researched": researched, "remaining": total - researched})
    coverage.sort(key=lambda row: (-row["total"], row["category"]))

    verdicts = Counter(e.get("human_verdict") or "not reviewed" for r in records for e in r.get("evidence", []))
    automated = Counter(e.get("claim_supported", "unverified") for r in records for e in r.get("evidence", []))
    evidence_quality = Counter()
    evidence_missing_excerpt = 0
    evidence_missing_title = 0
    evidence_missing_field = 0
    evidence_count = 0
    for record in records:
        for evidence in record.get("evidence", []):
            evidence_count += 1
            if evidence.get("excerpt"):
                quality = evidence.get("evidence_quality")
                if quality is None:
                    quality, _ = classify_excerpt(evidence["excerpt"])
            else:
                quality = "insufficient"
                evidence_missing_excerpt += 1
            evidence_quality[quality] += 1
            evidence_missing_title += not bool(evidence.get("source_title"))
            evidence_missing_field += not bool(evidence.get("field"))

    field_names = ["description", "auth_methods", "access_model", "api_type", "api_breadth", "mcp_status", "buildability", "blockers"]
    unknown_counts = Counter(
        field for record in records for field in field_names if contains_unknown(record.get(field))
    )
    field_status: dict[str, Counter[str]] = {field: Counter() for field in field_names}
    for record in records:
        mapped = {e.get("field") for e in record.get("evidence", []) if e.get("field")}
        for field in field_names:
            if contains_unknown(record.get(field)):
                state = "explicitly unknown / unclear"
            elif field in mapped:
                matching = [e for e in record.get("evidence", []) if e.get("field") == field]
                if any(e.get("human_verdict") == "supported" for e in matching):
                    state = "human sample supported"
                elif any(e.get("claim_supported") in {"supported", "partially_supported"} for e in matching):
                    state = "pipeline marked supported"
                elif any(e.get("excerpt") and e.get("retrieval_status") == "retrieved" for e in matching):
                    state = "evidence present; unverified"
                else:
                    state = "source incomplete / unverified"
            elif record.get("research_status") in {"not_researched", "blocked"}:
                state = "not established in this pass"
            else:
                state = "no field-linked evidence"
            field_status[field][state] += 1
    auth_counts: Counter[str] = Counter()
    access_counts: Counter[str] = Counter()
    api_counts: Counter[str] = Counter()
    build_counts: Counter[str] = Counter()
    for record in records:
        auth_counts.update(auth_families(record.get("auth_methods", [])))
        access_counts.update(access_flags(record.get("access_model", "")))
        api_counts[api_bucket(record.get("api_type", ""))] += 1
        build_counts[record.get("buildability", "missing / invalid")] += 1

    return {
        "assignment_total": len(app_rows),
        "record_total": len(records),
        "researched_total": sum(1 for r in records if r.get("research_status", "researched" if r.get("evidence") else "not_researched") in {"researched", "partial"}),
        "partial_total": sum(1 for r in records if r.get("research_status") == "partial"),
        "blocked_total": sum(1 for r in records if r.get("research_status") == "blocked"),
        "not_researched_total": sum(1 for r in records if r.get("research_status", "researched" if r.get("evidence") else "not_researched") == "not_researched"),
        "unresearched_total": max(0, len(app_rows) - sum(1 for r in records if r.get("research_status", "researched" if r.get("evidence") else "not_researched") in {"researched", "partial"})),
        "apps_with_usable_evidence": sum(1 for r in records if any(e.get("retrieval_status") == "retrieved" and e.get("excerpt") and (e.get("evidence_quality") == "usable" or (not e.get("evidence_quality") and classify_excerpt(e.get("excerpt"))[0] == "usable")) for e in r.get("evidence", []))),
        "apps_with_evidence": sum(1 for r in records if any(e.get("excerpt") for e in r.get("evidence", []))),
        "coverage_percent": round((sum(1 for r in records if r.get("research_status", "researched" if r.get("evidence") else "not_researched") in {"researched", "partial"}) / len(app_rows) * 100) if app_rows else 0, 1),
        "category_coverage": coverage,
        "field_status": field_status,
        "auth_families": auth_counts,
        "access_characteristics": access_counts,
        "api_surfaces": api_counts,
        "buildability": build_counts,
        "blocker_topics": blocker_topics(records),
        "unknown_fields": unknown_counts,
        "evidence_total": evidence_count,
        "evidence_quality": evidence_quality,
        "evidence_missing_excerpt": evidence_missing_excerpt,
        "evidence_missing_title": evidence_missing_title,
        "evidence_missing_field": evidence_missing_field,
        "human_verdicts": verdicts,
        "automated_claim_status": automated,
    }
