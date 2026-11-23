"""Small, conservative checks for whether a retrieved excerpt is readable text.

These checks assess excerpt quality only. They never decide whether a source
supports a claim; claim_supported remains unverified until review.
"""

import re

QUALITY_VALUES = {"usable", "page_shell", "navigation", "insufficient"}
_METADATA_LINE = re.compile(
    r"^(?:[-*]\s*)?(?:meta|title|link|script|style|itemprop|charset|name|property):\s*",
    re.IGNORECASE,
)
_HTTP_STATUS = re.compile(r"(?<!\d)(?:400|401|403|404|405|429|500|502|503)(?!\d)")


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
    links = re.findall(r"\[[^\]]*\]\([^)]*\)", cleaned)
    headings = [line for line in lines if re.match(r"^#{1,6}\s", line)]
    prose_lines = [line for line in lines if not line.startswith(("#", "|", "- ", "* ", ">"))]

    metadata_lines = [line for line in lines if _METADATA_LINE.match(line)]
    if len(metadata_lines) >= 2 and len(metadata_lines) / len(lines) >= 0.4:
        return "page_shell", "Excerpt is dominated by page metadata/title fields rather than documentation body text."

    # Some extracted API reference tables arrive flattened into one string.
    # A sequence of status/type/message labels is not useful context for a
    # claim, even when tokenization makes the string appear long enough.
    if re.search(r"status\s*type\s*message", cleaned, re.IGNORECASE) and len(_HTTP_STATUS.findall(cleaned)) >= 4:
        return "insufficient", "Excerpt is a flattened HTTP status/error table without row structure or endpoint context."

    linked_list_lines = [line for line in lines if line.startswith(("- ", "* ")) and re.search(r"\[[^\]]*\]\(", line)]
    if len(linked_list_lines) >= 2 and len(prose_lines) == 0:
        return "navigation", "Excerpt consists of linked index/navigation entries without explanatory prose."

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

