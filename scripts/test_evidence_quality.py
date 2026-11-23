"""Local examples for the evidence excerpt quality classifier (no network)."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from appscout.evidence_quality import classify_excerpt


EXAMPLES = [
    (
        "useful documentation",
        "The REST API uses OAuth 2.0 access tokens. Requests must include the token "
        "in the Authorization header. Tokens inherit the permissions granted to the user.",
        "usable",
    ),
    (
        "navigation",
        "[Overview](/docs/overview) [Authentication](/docs/auth) "
        "[Rate limits](/docs/limits) [API reference](/docs/reference)",
        "navigation",
    ),
    (
        "serialized page configuration",
        '{"docsConfig":{"theme":"mint","$schema":"https://mintlify.com/docs.json",'
        '"name":"Example","navigation":{"tabs":[]}}',
        "page_shell",
    ),
]


def main() -> int:
    for label, excerpt, expected in EXAMPLES:
        quality, reason = classify_excerpt(excerpt)
        assert quality == expected, f"{label}: expected {expected}, got {quality}"
        print(f"PASS {label}: {quality} - {reason}")
    print("All local evidence-quality examples passed; no web requests made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
