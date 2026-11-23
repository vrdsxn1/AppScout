"""Research a small number of apps with Firecrawl and save resumable results.

Run from the project root:
    .\\.venv\\Scripts\\python.exe scripts\\run_research.py --limit 3

The default output is output/research_results_v2.json. Incomplete evidence
retrieval is resumed from that file on the next run.
"""

import argparse
import atexit
import csv
import json
import os
import random
import re
import sys
import time
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from appscout.evidence_quality import classify_excerpt
APP_LIST_PATH = PROJECT_ROOT / "data" / "apps.csv"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "research_prompt.md"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "output" / "research_results_v2.json"
API_ROOT = "https://api.firecrawl.dev/v2"
REQUEST_TIMEOUT = (10, 60)
MAX_WAIT_SECONDS = 240
POLL_INTERVAL_SECONDS = 3
MAX_429_ATTEMPTS = 3
SOURCE_REQUEST_DELAY_SECONDS = 0.5


class RateLimitedError(RuntimeError):
    """Firecrawl still returned HTTP 429 after the limited retry attempts."""


class FirecrawlCreditsError(RuntimeError):
    """Firecrawl rejected the request because the account cannot make it."""


# The agent supplies research fields; assignment identity and check date are
# supplied locally. Evidence metadata is attached after we try to retrieve URLs.
RESEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "auth_methods": {"type": "array", "items": {"type": "string"}},
        "access_model": {"type": "string"},
        "api_type": {"type": "string"},
        "api_breadth": {"type": "string"},
        "mcp_status": {"type": "string"},
        "buildability": {
            "type": "string",
            "enum": ["build_now", "build_with_restrictions", "needs_outreach", "unclear"],
        },
        "blockers": {"type": "array", "items": {"type": "string"}},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "field": {"type": "string", "enum": ["description", "auth_methods", "access_model", "api_type", "api_breadth", "mcp_status", "buildability", "blockers"]},
                    "url": {"type": "string"},
                    "source_type": {"type": "string"},
                },
                "required": ["claim", "field", "url", "source_type"],
                "additionalProperties": False,
            },
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "description",
        "auth_methods",
        "access_model",
        "api_type",
        "api_breadth",
        "mcp_status",
        "buildability",
        "blockers",
        "evidence",
        "confidence",
    ],
    "additionalProperties": False,
}


def load_app_list() -> list[dict[str, str]]:
    with APP_LIST_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def load_saved_records(output_path: Path) -> list[dict[str, Any]]:
    if not output_path.exists():
        return []
    with output_path.open("r", encoding="utf-8") as output_file:
        saved = json.load(output_file)
    if not isinstance(saved, list):
        raise ValueError("Output JSON must contain a list of app records.")
    return saved


def save_records(output_path: Path, records: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as output_file:
        json.dump(records, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
    temporary_path.replace(output_path)


def release_lock(lock_path: Path, lock_handle: Any) -> None:
    lock_handle.close()
    lock_path.unlink(missing_ok=True)


def retry_after_seconds(response: requests.Response, retry_number: int) -> float:
    """Use Retry-After when valid; otherwise use short exponential backoff+jitter."""
    header = response.headers.get("Retry-After")
    if header:
        try:
            return max(0.0, float(header))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(header)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return min(8.0, 2 ** (retry_number - 1)) + random.uniform(0.0, 0.5)


def request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    for attempt in range(1, MAX_429_ATTEMPTS + 1):
        try:
            response = requests.request(
                method,
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.Timeout as exc:
            raise RuntimeError("Firecrawl request timed out.") from exc
        except requests.ConnectionError as exc:
            raise RuntimeError("Could not connect to Firecrawl; check the network.") from exc
        except requests.RequestException as exc:
            raise RuntimeError("Firecrawl request failed.") from exc

        if response.status_code == 429:
            if attempt == MAX_429_ATTEMPTS:
                raise RateLimitedError(
                    f"Firecrawl returned HTTP 429 after {MAX_429_ATTEMPTS} attempts."
                )
            delay = retry_after_seconds(response, attempt)
            print(f"  Firecrawl rate limited the request; retrying in {delay:.1f}s ({attempt}/{MAX_429_ATTEMPTS - 1}).")
            time.sleep(delay)
            continue

        if response.status_code == 402:
            raise FirecrawlCreditsError("Firecrawl returned HTTP 402 (Payment Required). Check account credits or billing.")

        if not response.ok:
            raise RuntimeError(f"Firecrawl returned HTTP {response.status_code} ({response.reason}).")
        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError("Firecrawl returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Firecrawl returned an invalid response object.")
        if result.get("success") is False:
            raise RuntimeError("Firecrawl reported that the request was unsuccessful.")
        return result

    raise RuntimeError("Firecrawl request ended unexpectedly.")


def research_app(app: dict[str, str], api_key: str, shared_prompt: str) -> dict[str, Any]:
    app_name = app["app_name"].strip()
    category = app["category"].strip()
    source_url = app["source_url"].strip()
    prompt = f"""{shared_prompt}

Research app: {app_name}
Assignment category: {category}
Assignment source URL: {source_url}

Find official API documentation, authentication requirements, pricing/access
requirements, and any official or existing MCP integration. Use Firecrawl web
search and page retrieval as needed. Return the requested JSON object only.
Every important finding must have a specific evidence record with a concise
claim and exact source URL. Keep claims atomic and preserve plan, scope, edition,
version, subscription, and rate-limit qualifiers. Do not assign Beta, GA,
deprecated, or preview labels without explicit source wording. A returned URL
does not by itself establish claim support. If a point is not established,
return `unknown` or `unclear` as directed by the shared rules."""

    started = request_json(
        "POST",
        f"{API_ROOT}/agent",
        api_key,
        {"prompt": prompt, "schema": RESEARCH_SCHEMA, "mode": "extract"},
    )
    job_id = started.get("id")
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError("Firecrawl did not return a research job ID.")

    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        status_result = request_json("GET", f"{API_ROOT}/agent/{job_id}", api_key)
        status = status_result.get("status")
        if status == "completed":
            data = status_result.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Completed Firecrawl job did not contain structured data.")
            return data
        if status in {"failed", "cancelled", "error"}:
            raise RuntimeError(f"Firecrawl research job ended with status: {status}.")
    raise RuntimeError("Firecrawl research job did not finish within four minutes.")


STOP_WORDS = {
    "about", "after", "also", "among", "and", "api", "available", "based",
    "before", "claim", "data", "from", "into", "only", "official", "that",
    "the", "their", "this", "through", "using", "with", "when", "where",
}


def find_relevant_excerpt(markdown: str, claim: str, max_length: int = 500) -> str | None:
    """Choose a short readable body passage; selection is not claim verification."""
    claim_terms = {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9.-]{3,}", claim)
        if word.lower() not in STOP_WORDS
    }
    paragraphs = [" ".join(part.split()) for part in re.split(r"\n\s*\n", markdown) if part.strip()]
    paragraphs = [paragraph for paragraph in paragraphs if classify_excerpt(paragraph)[0] == "usable"]
    if not claim_terms or not paragraphs:
        return None
    best = max(
        paragraphs,
        key=lambda paragraph: sum(term in paragraph.lower() for term in claim_terms),
    )
    score = sum(term in best.lower() for term in claim_terms)
    if score == 0:
        return None
    if len(best) > max_length:
        best = best[: max_length - 1].rsplit(" ", 1)[0] + "…"
    return best


def retrieve_evidence(evidence: dict[str, Any], api_key: str) -> None:
    """Fetch one evidence page, attach source context, and leave support unverified."""
    result = request_json(
        "POST",
        f"{API_ROOT}/scrape",
        api_key,
        {"url": evidence["url"], "formats": ["markdown"], "onlyMainContent": True},
    )
    data = result.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("markdown"), str):
        raise RuntimeError("Firecrawl response did not contain page markdown.")
    markdown = data["markdown"]
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        title = metadata.get("title")
        if isinstance(title, str) and title.strip():
            evidence["source_title"] = title.strip()
    evidence["excerpt"] = find_relevant_excerpt(markdown, evidence["claim"])
    evidence["retrieval_status"] = "retrieved" if markdown.strip() else "inaccessible"
    evidence["claim_supported"] = "unverified"
    quality, quality_note = classify_excerpt(evidence["excerpt"])
    evidence["evidence_quality"] = quality
    evidence["evidence_quality_note"] = quality_note
    evidence["retrieval_note"] = None if quality == "usable" else "Page retrieved, but no usable body-text excerpt was extracted."


def complete_evidence(
    record: dict[str, Any],
    api_key: str,
    output_path: Path,
    saved_records: list[dict[str, Any]],
    record_index: int,
) -> str | None:
    """Retrieve pending sources. Return a stop reason when service access is blocked."""
    for item in record.get("evidence", []):
        item.setdefault("retrieval_status", "not_attempted")
        item.setdefault("claim_supported", "unverified")
        item.setdefault("source_title", None)
        item.setdefault("excerpt", None)
        item.setdefault("retrieval_note", None)
        item.setdefault("evidence_quality", "insufficient")
        item.setdefault("evidence_quality_note", "No excerpt quality assessment is available.")

    for evidence in record.get("evidence", []):
        if evidence.get("retrieval_status") == "retrieved" and evidence.get("evidence_quality"):
            continue
        url = str(evidence.get("url", ""))
        print(f"  Retrieving evidence page: {url}")
        try:
            retrieve_evidence(evidence, api_key)
            print("    Page retrieved; claim support remains unverified pending review.")
        except RateLimitedError:
            evidence["retrieval_status"] = "rate_limited"
            evidence["claim_supported"] = "unverified"
            evidence["retrieval_note"] = f"HTTP 429 after {MAX_429_ATTEMPTS} attempts."
            saved_records[record_index] = record
            save_records(output_path, saved_records)
            print(f"    Rate limited after {MAX_429_ATTEMPTS} attempts: {url}")
            return "rate_limited"
        except FirecrawlCreditsError as exc:
            evidence["retrieval_status"] = "inaccessible"
            evidence["claim_supported"] = "unverified"
            evidence["evidence_quality"] = "insufficient"
            evidence["evidence_quality_note"] = "No excerpt could be assessed because Firecrawl access was blocked."
            evidence["retrieval_note"] = str(exc)
            saved_records[record_index] = record
            save_records(output_path, saved_records)
            print(f"    Stopping source retrieval: {exc}")
            return "credits_unavailable"
        except RuntimeError as exc:
            evidence["retrieval_status"] = "inaccessible"
            evidence["claim_supported"] = "unverified"
            evidence["retrieval_note"] = str(exc)
            print(f"    Could not retrieve page: {exc}")
        saved_records[record_index] = record
        save_records(output_path, saved_records)
        time.sleep(SOURCE_REQUEST_DELAY_SECONDS)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Research apps from data/apps.csv using Firecrawl.")
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum new apps to research in assignment order (default: 3); saved incomplete records resume first.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output file (default: output/research_results_v2.json; baseline is never read or overwritten).",
    )
    parser.add_argument(
        "--apps",
        help="Optional comma-separated app names to process instead of the next apps in assignment order.",
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output_path.with_suffix(output_path.suffix + ".lock")
    try:
        lock_handle = lock_path.open("x", encoding="utf-8")
        lock_handle.write(f"pid={os.getpid()}\n")
    except FileExistsError:
        print(f"Another research run appears active (lock file: {lock_path}).")
        print("If a previous run was forcibly stopped, remove that stale lock and resume.")
        return 1
    atexit.register(release_lock, lock_path, lock_handle)

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        print("Error: FIRECRAWL_API_KEY is missing or blank in the project .env file.")
        return 1

    try:
        from appscout.models import AppResearchRecord

        apps = load_app_list()
        saved_records = load_saved_records(output_path)
        shared_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error reading project input/output files: {exc}")
        return 1

    saved_indices = {
        record.get("app_name", "").casefold(): index
        for index, record in enumerate(saved_records)
    }
    # Resume any saved app with pending evidence, then add up to --limit new
    # apps in original assignment order. Completed v2 records are left alone;
    # the baseline file is never consulted for selection or skip decisions.
    incomplete_existing = [
        app
        for app in apps
        if app.get("app_name", "").strip().casefold() in saved_indices
        and any(
            evidence.get("retrieval_status") != "retrieved"
            for evidence in saved_records[saved_indices[app["app_name"].strip().casefold()]].get("evidence", [])
        )
    ]
    new_apps = [
        app for app in apps
        if app.get("app_name", "").strip().casefold() not in saved_indices
    ][: args.limit]
    if args.apps:
        requested = [name.strip().casefold() for name in args.apps.split(",") if name.strip()]
        selected = [app for app in apps if app.get("app_name", "").strip().casefold() in requested]
        found = {app.get("app_name", "").strip().casefold() for app in selected}
        if set(requested) != found:
            parser.error(f"Unknown app name(s): {', '.join(sorted(set(requested) - found))}")
        if len(selected) > args.limit:
            parser.error("--limit cannot be lower than the number of names passed to --apps")
    else:
        selected = incomplete_existing + new_apps
    if not selected:
        print("No new apps or incomplete v2 records need processing.")
        return 0
    print(
        f"Queued {len(incomplete_existing)} incomplete v2 record(s) for resume "
        f"and {len(new_apps)} new app(s)."
    )

    stop_reason: tuple[str, str, str] | None = None
    errors: list[str] = []
    processed: list[str] = []
    skipped: list[str] = []

    for index, app in enumerate(selected, start=1):
        app_name = app.get("app_name", "").strip()
        key = app_name.casefold()
        if key in saved_indices:
            record_index = saved_indices[key]
            record = saved_records[record_index]
            print(f"[{index}/{len(selected)}] Resuming evidence for {app_name} from the v2 output...")
        else:
            print(f"[{index}/{len(selected)}] Researching {app_name}...")
            try:
                research = research_app(app, api_key, shared_prompt)
                record_data = {
                    **research,
                    "app_name": app_name,
                    "category": app["category"].strip(),
                    "last_checked": date.today().isoformat(),
                }
                record_data["evidence"].append(
                    {
                        "claim": f"The assignment lists {app_name} in the {app['category'].strip()} category.",
                        "field": "category",
                        "url": app["source_url"].strip(),
                        "source_type": "assignment list",
                    }
                )
                record = AppResearchRecord.model_validate(record_data).model_dump(mode="json")
                saved_records.append(record)
                record_index = len(saved_records) - 1
                saved_indices[key] = record_index
                save_records(output_path, saved_records)
                print(f"  Saved validated research record for {app_name} before source retrieval.")
            except RateLimitedError:
                stop_reason = (app_name, "Firecrawl research-agent request", "rate_limited")
                print(f"  Firecrawl remained rate-limited while researching {app_name}; stopping.")
                break
            except FirecrawlCreditsError as exc:
                stop_reason = (app_name, "Firecrawl research-agent request", str(exc))
                print(f"  Firecrawl access is blocked while researching {app_name}; stopping: {exc}")
                break
            except (RuntimeError, ValidationError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"{app_name}: {exc}")
                print(f"  Error: {app_name}: {exc}")
                continue

        if not any(e.get("retrieval_status") != "retrieved" for e in record.get("evidence", [])):
            skipped.append(app_name)
            print("  All evidence pages were already retrieved; leaving the record unchanged.")
            continue
        try:
            evidence_stop = complete_evidence(record, api_key, output_path, saved_records, record_index)
            if evidence_stop:
                pending_url = next(
                    (e.get("url", "") for e in record.get("evidence", []) if e.get("retrieval_status") in {"rate_limited", "inaccessible"}),
                    "unknown source",
                )
                stop_reason = (app_name, str(pending_url), evidence_stop)
                break
            processed.append(app_name)
            print(f"  Finished source retrieval for {app_name}.")
        except (ValidationError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{app_name}: {exc}")
            print(f"  Error updating evidence for {app_name}: {exc}")

    print(f"\nCompleted this run: {', '.join(processed) if processed else 'none'}")
    print(f"Already complete: {', '.join(skipped) if skipped else 'none'}")
    print(f"Other errors: {len(errors)}")
    for error in errors:
        print(f"  - {error}")
    if stop_reason:
        app_name, source, reason = stop_reason
        print(f"Stopped: {app_name} at {source}: {reason}")
        print("Completed records and source statuses are saved. Resume later with the same command.")
    print(f"Output: {output_path}")
    return 2 if stop_reason else (1 if errors else 0)


if __name__ == "__main__":
    sys.exit(main())
