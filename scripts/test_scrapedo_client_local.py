"""Offline mocked checks for Scrape.do diagnostics and smoke-test resilience."""

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests

import appscout.scrapedo_client as scrapedo_client
import scripts.smoke_test_scrapedo as smoke_test
from appscout.scrapedo_client import ScrapeDoError, ScrapeDoHTTPError, fetch_page, scrape_do_diagnostics

TEST_TOKEN = "test-only-secret-token"
DOC_BODY = "# API documentation\n\n" + "Readable API documentation text. " * 10


class FakeResponse:
    def __init__(self, status=200, body=DOC_BODY, headers=None):
        self.status_code = status
        self.content = body.encode("utf-8")
        self.text = body
        self.headers = headers or {"Content-Type": "text/markdown"}
        self.ok = 200 <= status < 400

    def json(self):
        import json

        return json.loads(self.text)


def main() -> int:
    old_token = os.environ.get("SCRAPEDO_API_TOKEN")
    os.environ["SCRAPEDO_API_TOKEN"] = TEST_TOKEN
    old_root = scrapedo_client.PROJECT_ROOT
    scrapedo_client.PROJECT_ROOT = ROOT
    captured = []
    original_get = requests.get
    url = "https://docs.example.test/api?type=public&version=2"

    try:
        def successful_get(endpoint, *, params, timeout):
            captured.append((endpoint, params.copy(), timeout))
            return FakeResponse(headers={
                "content-type": "text/markdown",
                "scrape.do-request-cost": "1",
                "Scrape.do-Remaining-Credits": "999",
            })

        requests.get = successful_get
        response = fetch_page(url)
        assert response.status_code == 200
        assert captured[-1][2] == 25
        endpoint, params, _ = captured[-1]
        assert endpoint == "https://api.scrape.do/"
        assert params["url"] == url and params["output"] == "markdown"
        assert "render" not in params
        prepared = requests.Request("GET", endpoint, params=params).prepare()
        assert "url=https%3A%2F%2Fdocs.example.test%2Fapi%3Ftype%3Dpublic%26version%3D2" in prepared.url
        info = scrape_do_diagnostics(response.headers, TEST_TOKEN)
        assert info["request_cost"] == "1" and info["remaining_credits"] == "999"
        assert info["request_cost"] != info["remaining_credits"]
        print("PASS Request-Cost=1 and Remaining-Credits=999 are reported separately; timeout=25")

        info = scrape_do_diagnostics({"SCRAPE.DO-REMAINING-CREDITS": "999"}, TEST_TOKEN)
        assert info["request_cost"] is None and info["remaining_credits"] == "999"
        print("PASS missing Request-Cost remains unknown; balance is not substituted")

        error_headers = {
            "CONTENT-TYPE": "text/plain",
            "Scrape.do-Request-Cost": "1",
            "scrape.do-Remaining-Credits": "999",
            "Scrape.do-Error": "invalid output parameter",
            "Authorization": f"Bearer {TEST_TOKEN}",
            "Set-Cookie": "session=private",
            "X-Debug-Url": f"https://api.scrape.do/?token={TEST_TOKEN}",
        }
        long_body = f"Invalid parameter token={TEST_TOKEN}; " + ("bad request detail " * 50)
        requests.get = lambda *args, **kwargs: FakeResponse(status=400, body=long_body, headers=error_headers)
        try:
            fetch_page(url)
            raise AssertionError("HTTP 400 was not surfaced")
        except ScrapeDoHTTPError as exc:
            assert exc.status_code == 400
            assert exc.request_cost == "1" and exc.remaining_credits == "999"
            assert TEST_TOKEN not in exc.diagnostic_body
            assert len(exc.diagnostic_body) <= scrapedo_client.MAX_DIAGNOSTIC_BODY + 1
            assert "Authorization" not in exc.diagnostic_headers
            assert "set-cookie" not in exc.diagnostic_headers
            assert "x-debug-url" not in exc.diagnostic_headers
            assert exc.diagnostic_headers["scrape.do-error"] == "invalid output parameter"
        print("PASS HTTP 400 has a bounded sanitized body and whitelisted case-insensitive headers")

        for failure, label in ((requests.Timeout(f"token={TEST_TOKEN}"), "timeout"),
                               (requests.ConnectionError(f"token={TEST_TOKEN}"), "connection error")):
            requests.get = lambda *args, _failure=failure, **kwargs: (_ for _ in ()).throw(_failure)
            try:
                fetch_page(url)
                raise AssertionError(f"{label} was not surfaced")
            except ScrapeDoError as exc:
                assert TEST_TOKEN not in str(exc)
                assert url not in str(exc)
                if label == "timeout":
                    assert "timed out after 25 seconds" in str(exc)
        print("PASS timeout and connection errors are safe, explicit failures")

        sources = smoke_test.SOURCES
        calls = []
        smoke_test.SOURCES = [("GitHub", "https://docs.github.com/en/rest"),
                              ("Stripe", "https://docs.stripe.com/api"),
                              ("Notion", "https://developers.notion.com/reference/intro")]
        smoke_test.get_token = lambda: TEST_TOKEN
        smoke_test.robots_allow = lambda target: (True, "mock robots allowed")

        def sequence_fetch(target, **kwargs):
            calls.append(target)
            if len(calls) == 1:
                raise ScrapeDoHTTPError(400, "text/plain", None, "999", "invalid parameter", {"scrape.do-error": "invalid parameter"})
            return FakeResponse()

        smoke_test.fetch_page = sequence_fetch
        output = io.StringIO()
        with patch.object(sys, "argv", ["smoke_test_scrapedo.py"]), contextlib.redirect_stdout(output):
            exit_code = smoke_test.main()
        rendered = output.getvalue()
        assert exit_code == 1 and len(calls) == 3
        assert all(name in rendered for name in ("[GitHub]", "[Stripe]", "[Notion]"))
        assert "[Stripe] https://docs.stripe.com/api" in rendered
        assert "source_access=mock robots allowed" in rendered and "fetch=success" in rendered
        assert "request_cost=unknown" in rendered and "remaining_credits=999" in rendered
        assert TEST_TOKEN not in rendered and "token=" not in rendered
        smoke_test.SOURCES = sources
        print("PASS smoke test continues through all three URLs after the HTTP 400 failure")

        timeout_calls = []
        def timeout_then_success(target, **kwargs):
            timeout_calls.append(target)
            if len(timeout_calls) == 1:
                raise requests.Timeout(f"request url contains token={TEST_TOKEN}")
            return FakeResponse()
        smoke_test.fetch_page = timeout_then_success
        output = io.StringIO()
        with patch.object(sys, "argv", ["smoke_test_scrapedo.py"]), contextlib.redirect_stdout(output):
            exit_code = smoke_test.main()
        rendered = output.getvalue()
        assert exit_code == 1 and len(timeout_calls) == 3
        assert "request timed out" in rendered and "[Stripe]" in rendered and "[Notion]" in rendered
        assert TEST_TOKEN not in rendered and "token=" not in rendered
        print("PASS smoke test reports a timeout and continues to the remaining URLs")

        with tempfile.TemporaryDirectory() as empty_project:
            os.environ.pop("SCRAPEDO_API_TOKEN", None)
            scrapedo_client.PROJECT_ROOT = Path(empty_project)
            calls_before = len(captured)
            try:
                fetch_page(url)
                raise AssertionError("Missing token was not rejected")
            except ScrapeDoError as exc:
                assert "SCRAPEDO_API_TOKEN" in str(exc)
            assert len(captured) == calls_before
        print("PASS missing token fails before any HTTP request")
    finally:
        requests.get = original_get
        scrapedo_client.PROJECT_ROOT = old_root
        if old_token is None:
            os.environ.pop("SCRAPEDO_API_TOKEN", None)
        else:
            os.environ["SCRAPEDO_API_TOKEN"] = old_token
    print("All diagnostics tests used mocked responses; no network requests made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
