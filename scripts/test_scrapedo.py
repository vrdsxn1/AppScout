"""Explicit one-URL Scrape.do connection check. Never called by validation."""

import argparse
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from appscout.scrapedo_client import (  # noqa: E402
    ScrapeDoError,
    ScrapeDoHTTPError,
    fetch_page,
    get_token,
    scrape_do_diagnostics,
)


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


def safe_preview(body: str, secret: str) -> str:
    parser = TextOnly()
    try:
        parser.feed(body)
        text = " ".join(parser.parts)
    except Exception:
        text = body
    text = html.unescape(text)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)(token\s*[=:]\s*)[^\s&,;]+", r"\1[REDACTED]", text)
    text = " ".join(text.split())
    return text[:240] + ("…" if len(text) > 240 else "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Make one explicit Scrape.do request for the supplied public URL.")
    parser.add_argument("url", help="One public HTTP or HTTPS target URL")
    parser.add_argument("--render", action="store_true", help="Explicitly request JavaScript rendering; may cost more credits.")
    parser.add_argument("--output", choices=("markdown", "html"), default="markdown")
    args = parser.parse_args()

    try:
        token = get_token()
        response = fetch_page(args.url, render=args.render, output=args.output)
    except ScrapeDoHTTPError as exc:
        print(f"HTTP error: status={exc.status_code}; content_type={exc.content_type or 'unknown'}")
        print(f"request_cost={exc.request_cost if exc.request_cost is not None else 'unknown'}")
        print(f"remaining_credits={exc.remaining_credits if exc.remaining_credits is not None else 'unknown'}")
        if exc.status_code == 400:
            print(f"response_body_preview={exc.diagnostic_body or '[empty]'}")
            print(f"diagnostic_headers={exc.diagnostic_headers or '[none]'}")
        return 1
    except ScrapeDoError as exc:
        print(f"Scrape.do error: {exc}")
        return 1

    print(f"Success: status={response.status_code}")
    print(f"content_type={response.headers.get('Content-Type', 'unknown')}")
    print(f"character_count={len(response.text)}")
    diagnostics = scrape_do_diagnostics(response.headers, token)
    print(f"request_cost={diagnostics['request_cost'] if diagnostics['request_cost'] is not None else 'unknown'}")
    print(f"remaining_credits={diagnostics['remaining_credits'] if diagnostics['remaining_credits'] is not None else 'unknown'}")
    print(f"preview={safe_preview(response.text, token)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
