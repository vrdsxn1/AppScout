"""Small Scrape.do HTTP client. Importing this module never makes a request."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.scrape.do/"
DEFAULT_TIMEOUT = 25
ALLOWED_OUTPUTS = {"markdown", "html"}
MAX_DIAGNOSTIC_BODY = 500
SAFE_DIAGNOSTIC_HEADERS = {
    "content-type",
    "scrape.do-error",
    "scrape.do-error-message",
    "scrape.do-request-cost",
    "scrape.do-remaining-credits",
    "scrape.do-status-code",
}


class ScrapeDoError(RuntimeError):
    """A safe-to-display error that never includes a request URL or token."""


class ScrapeDoHTTPError(ScrapeDoError):
    def __init__(
        self,
        status_code: int,
        content_type: str = "",
        request_cost: str | None = None,
        remaining_credits: str | None = None,
        diagnostic_body: str = "",
        diagnostic_headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.content_type = content_type
        self.request_cost = request_cost
        self.remaining_credits = remaining_credits
        self.diagnostic_body = diagnostic_body
        self.diagnostic_headers = diagnostic_headers or {}
        super().__init__(f"Scrape.do returned HTTP {status_code}.")


def get_token() -> str:
    """Load and return the configured token, or raise a safe actionable error."""
    env_path = PROJECT_ROOT / ".env"
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        # Keep this one-variable setup usable before optional research extras
        # are installed. Never display the parsed value.
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                name, separator, value = line.partition("=")
                if separator and name.strip() == "SCRAPEDO_API_TOKEN":
                    value = value.strip().strip("\"'")
                    os.environ.setdefault("SCRAPEDO_API_TOKEN", value)
                    break
    token = os.getenv("SCRAPEDO_API_TOKEN", "").strip()
    if not token:
        raise ScrapeDoError(
            "SCRAPEDO_API_TOKEN is missing. Add it to the project-root .env file."
        )
    return token


def _redact(text: str, token: str) -> str:
    if token:
        text = text.replace(token, "[REDACTED]")
    text = re.sub(r"(?i)https?://api\.scrape\.do/\?[^\s\"'<>]+", "https://api.scrape.do/?[REDACTED]", text)
    text = re.sub(r"(?i)([?&]token(?:=|%3d))[^&\s\"'<>]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(\btoken\s*[=:]\s*)[^\s&,;\"'<>]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", text)
    return " ".join(text.split())


def scrape_do_diagnostics(headers: Any, token: str = "") -> dict[str, Any]:
    """Read exact Scrape.do cost/balance headers and a safe diagnostic whitelist."""
    normalized = {str(name).casefold(): str(value) for name, value in headers.items()}
    request_cost = normalized.get("scrape.do-request-cost")
    remaining = normalized.get("scrape.do-remaining-credits")
    safe_headers = {
        name: _redact(value[:200], token)
        for name, value in normalized.items()
        if name in SAFE_DIAGNOSTIC_HEADERS
    }
    return {
        "request_cost": _redact(request_cost, token) if request_cost is not None else None,
        "remaining_credits": _redact(remaining, token) if remaining is not None else None,
        "headers": safe_headers,
    }


def _header_value(headers: Any, wanted: str) -> str:
    wanted = wanted.casefold()
    for name, value in headers.items():
        if str(name).casefold() == wanted:
            return str(value)
    return ""


def fetch_page(url: str, render: bool = False, output: str = "markdown") -> requests.Response:
    """Fetch one public URL through Scrape.do and return its successful response.

    The target URL is passed through requests' ``params`` encoding. JavaScript
    rendering is omitted unless ``render=True``. ``output`` may be ``markdown``
    or ``html``. No request is made until this function is explicitly called.
    """
    if not isinstance(url, str) or not url.strip():
        raise ScrapeDoError("A non-empty target URL is required.")
    if not url.startswith(("https://", "http://")):
        raise ScrapeDoError("Target URL must use HTTP or HTTPS.")
    if output not in ALLOWED_OUTPUTS:
        raise ScrapeDoError("output must be either 'markdown' or 'html'.")
    if not isinstance(render, bool):
        raise ScrapeDoError("render must be True or False.")

    token = get_token()
    params = {"token": token, "url": url, "output": output}
    if render:
        params["render"] = "true"

    try:
        response = requests.get(ENDPOINT, params=params, timeout=DEFAULT_TIMEOUT)
    except requests.Timeout:
        raise ScrapeDoError(f"Scrape.do request timed out after {DEFAULT_TIMEOUT} seconds.") from None
    except requests.ConnectionError:
        raise ScrapeDoError("Scrape.do connection failed.") from None
    except requests.RequestException as exc:
        # Do not include str(exc): it can contain the full URL and query token.
        raise ScrapeDoError(f"Scrape.do request failed ({type(exc).__name__}).") from None

    if not response.ok:
        diagnostics = scrape_do_diagnostics(response.headers, token)
        body = _redact(response.text[:MAX_DIAGNOSTIC_BODY], token)
        if len(response.text) > MAX_DIAGNOSTIC_BODY:
            body += "…"
        raise ScrapeDoHTTPError(
            response.status_code,
            _header_value(response.headers, "Content-Type"),
            diagnostics["request_cost"],
            diagnostics["remaining_credits"],
            body,
            diagnostics["headers"],
        )

    content_type = _header_value(response.headers, "Content-Type").lower()
    if not response.content:
        raise ScrapeDoError("Scrape.do returned an empty response.")
    if not (
        content_type.startswith("text/")
        or "html" in content_type
        or "json" in content_type
        or "xml" in content_type
    ):
        raise ScrapeDoError("Scrape.do returned a non-text response.")
    if "json" in content_type:
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError):
            raise ScrapeDoError("Scrape.do returned invalid JSON.") from None
        if isinstance(payload, dict) and payload.get("error"):
            raise ScrapeDoError("Scrape.do returned an API error response.")

    return response
