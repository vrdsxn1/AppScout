"""Small, conservative checks for whether a retrieved excerpt is readable text.

These checks assess excerpt quality only. They never decide whether a source
supports a claim; claim_supported remains unverified until review.
"""

import json
import re

QUALITY_VALUES = {"usable", "page_shell", "navigation", "insufficient"}


def classify_excerpt(text: str | None) -> tuple[str, str]:
    """Classify excerpt readability and obvious extraction failures."""
    if not text or not text.strip():
        return "insufficient", "No readable excerpt text was extracted."

    cleaned = text.strip()
    if cleaned.startswith(("{", "[")):
        lowered = cleaned.lower()
        if any(key in lowered for key in ("docsconfig", "schema.json", "navigation", "sidebar")):
            return "page_shell", "Excerpt is serialized documentation configuration, not page body text."

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    words = re.findall(r"\b[\w'-]+\b", cleaned)
    links = re.findall(r"\[[^\]]+\]\([^)]*\)", cleaned)
    headings = [line for line in lines if re.match(r"^#{1,6}\s", line)]
    prose_lines = [line for line in lines if not line.startswith(("#", "|", "- ", "* ", ">"))]
    if len(words) < 12 or (headings and not prose_lines):
        return "insufficient", "Excerpt is too short or contains headings without explanatory body text."
    if links and len(links) >= 3 and len(words) < 70:
        return "navigation", "Excerpt is dominated by linked menu or index entries."

    table_lines = [line for line in lines if line.startswith("|")]
    if table_lines and len(table_lines) / max(1, len(lines)) > 0.65:
        return "insufficient", "Excerpt is table-only; its relevance and row meaning are not established here."

    if len(words) < 25:
        return "insufficient", "Excerpt has too little explanatory text for reliable review."
    return "usable", "Readable body text was extracted; this does not establish claim support."

