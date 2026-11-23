"""Manually triggered three-page Scrape.do smoke test; makes no batch crawl."""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from appscout.evidence_quality import classify_excerpt  # noqa: E402
from appscout.scrapedo_client import (  # noqa: E402
    ScrapeDoError,
    ScrapeDoHTTPError,
    fetch_page,
    get_token,
    scrape_do_diagnostics,
)

SOURCES = [
    ("GitHub", "https://docs.github.com/en/rest"),
    ("Stripe", "https://docs.stripe.com/api"),
    ("Notion", "https://developers.notion.com/reference/intro"),
]
USER_AGENT = "AppScoutTakeHomeResearch/1.0 (polite public documentation reader)"


def robots_allow(url: str) -> tuple[bool, str]:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        response = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=25)
    except requests.RequestException as exc:
        return False, f"robots.txt request failed ({type(exc).__name__}); fail closed"
    if response.status_code in (401, 403, 429) or response.status_code >= 500:
        return False, f"robots.txt returned HTTP {response.status_code}; fail closed"
    if response.status_code in (404, 410):
        return True, "no robots file"
    if not response.ok:
        return False, f"robots.txt returned HTTP {response.status_code}; fail closed"
    parser = RobotFileParser(robots_url)
    parser.parse(response.text.splitlines())
    if not parser.can_fetch(USER_AGENT, url):
        return False, "disallowed by robots.txt"
    return True, "allowed by robots.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch exactly three official documentation URLs once.")
    parser.add_argument("--render", action="store_true", help="Explicitly render all three pages with JavaScript.")
    args = parser.parse_args()
    try:
        token = get_token()
    except ScrapeDoError as exc:
        print(f"Scrape.do error: {exc}")
        return 2

    failed = False
    for app_name, url in SOURCES:
        print(f"[{app_name}] {url}")
        allowed, robots_note = robots_allow(url)
        if not allowed:
            failed = True
            print(f"  fetch=skipped; {robots_note}")
            continue
        print(f"  source_access={robots_note}")
        try:
            response = fetch_page(url, render=args.render, output="markdown")
        except ScrapeDoHTTPError as exc:
            failed = True
            print(f"  fetch=failed; HTTP {exc.status_code}; content_type={exc.content_type or 'unknown'}")
            print(f"  request_cost={exc.request_cost if exc.request_cost is not None else 'unknown'}")
            print(f"  remaining_credits={exc.remaining_credits if exc.remaining_credits is not None else 'unknown'}")
            if exc.status_code == 400:
                print(f"  response_body_preview={exc.diagnostic_body or '[empty]'}")
                print(f"  diagnostic_headers={exc.diagnostic_headers or '[none]'}")
            continue
        except requests.Timeout:
            failed = True
            print("  fetch=failed; Scrape.do request timed out; continuing to next URL")
            continue
        except requests.ConnectionError:
            failed = True
            print("  fetch=failed; Scrape.do connection error; continuing to next URL")
            continue
        except requests.RequestException as exc:
            failed = True
            print(f"  fetch=failed; request error ({type(exc).__name__}); continuing to next URL")
            continue
        except ScrapeDoError as exc:
            failed = True
            print(f"  fetch=failed; {exc}")
            continue

        quality, reason = classify_excerpt(response.text)
        content_type = next((str(value) for name, value in response.headers.items() if str(name).casefold() == "content-type"), "unknown")
        print(f"  fetch=success; status={response.status_code}; content_type={content_type}")
        print(f"  character_count={len(response.text)}; readable_documentation={quality == 'usable'}; excerpt_quality={quality}")
        print(f"  quality_note={reason}")
        diagnostics = scrape_do_diagnostics(response.headers, token)
        print(f"  request_cost={diagnostics['request_cost'] if diagnostics['request_cost'] is not None else 'unknown'}")
        print(f"  remaining_credits={diagnostics['remaining_credits'] if diagnostics['remaining_credits'] is not None else 'unknown'}")
        if args.render:
            print(f"  rendering=used explicitly; standard-fetch sufficiency was not measured in this run")
        elif quality == "usable":
            print("  rendering=not needed for this smoke check; normal fetch returned readable text")
        else:
            print("  rendering=not tested; retry this page with --render only if JavaScript rendering is authorized")

    print("No claim was marked supported; this test checks retrieval and readability only.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
