"""Polite, no-key research pass over public app sites (no paid services).

The script uses only official-site URL seeds plus links found on those pages.
It never submits login forms, solves challenges, bypasses robots, or retries 403/429.
Results are saved after every page and can be resumed without refetching attempted
URLs. Search-result pages are not scraped; unknowns stay unknown.
"""

import argparse
import csv
import html
import json
import random
import re
import sys
import threading
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from appscout.evidence_quality import classify_excerpt
from appscout.models import AppResearchRecord

APP_LIST = PROJECT_ROOT / "data" / "apps.csv"
BASELINE_V2 = PROJECT_ROOT / "output" / "research_results_v2.json"
OUTPUT = PROJECT_ROOT / "output" / "research_results_free.json"
USER_AGENT = "AppScoutTakeHomeResearch/1.0 (polite public documentation reader)"
PER_HOST_DELAY = 1.0
MAX_PAGES_PER_APP = 5
TIMEOUT = (8, 18)

# Candidate destinations only. A URL is used as evidence only after a public
# page is fetched successfully and its title/text is consistent with the app.
SITE_URLS = {
    "Front": "https://front.com/",
    "Pylon": "https://usepylon.com/",
    "LiveAgent": "https://www.liveagent.com/",
    "Plain": "https://plain.com/",
    "Help Scout": "https://www.helpscout.com/",
    "Gorgias": "https://www.gorgias.com/",
    "Gladly": "https://www.gladly.com/",
    "Slack": "https://slack.com/",
    "Twilio": "https://www.twilio.com/docs/",
    "Zoho Cliq": "https://www.zoho.com/cliq/",
    "Lark (Larksuite)": "https://www.larksuite.com/",
    "Pumble": "https://pumble.com/",
    "Discord": "https://discord.com/developers/docs/",
    "Telegram": "https://core.telegram.org/bots/api",
    "WhatsApp Business": "https://business.whatsapp.com/",
    "Aircall": "https://aircall.io/",
    "Vonage": "https://developer.vonage.com/",
    "Google Ads": "https://developers.google.com/google-ads/api/docs/start",
    "Meta Ads": "https://developers.facebook.com/docs/marketing-apis/",
    "LinkedIn Ads": "https://www.linkedin.com/developers/",
    "GoHighLevel": "https://marketplace.gohighlevel.com/docs/",
    "Mailchimp": "https://mailchimp.com/developer/marketing/api/",
    "Klaviyo": "https://developers.klaviyo.com/en/reference/api-overview",
    "systeme.io": "https://systeme.io/",
    "Pinterest": "https://developers.pinterest.com/docs/api/v5/",
    "Threads (Meta)": "https://developers.facebook.com/docs/threads/",
    "SendGrid": "https://www.twilio.com/docs/sendgrid/api-reference",
    "Shopify": "https://shopify.dev/docs/api",
    "WooCommerce": "https://developer.woocommerce.com/docs/",
    "BigCommerce": "https://developer.bigcommerce.com/docs/",
    "Salesforce Commerce Cloud": "https://developer.salesforce.com/docs/commerce/commerce-api/guide",
    "Magento (Adobe Commerce)": "https://developer.adobe.com/commerce/webapi/rest/",
    "Squarespace": "https://developers.squarespace.com/",
    "Ecwid": "https://docs.ecwid.com/",
    "Gumroad": "https://gumroad.com/api",
    "Amazon Selling Partner": "https://developer-docs.amazon.com/sp-api/",
    "fanbasis": "https://fanbasis.com/",
    "DataForSEO": "https://docs.dataforseo.com/",
    "SE Ranking": "https://seranking.com/",
    "Ahrefs": "https://docs.ahrefs.com/",
    "MrScraper": "https://mrscraper.com/",
    "Apify": "https://docs.apify.com/api/v2/",
    "Firecrawl": "https://docs.firecrawl.dev/",
    "Bright Data": "https://docs.brightdata.com/",
    "Sherlock": "https://www.sherlock.xyz/",
    "Waterfall.io": "https://waterfall.io/",
    "Clay": "https://www.clay.com/",
    "GitHub": "https://docs.github.com/en/rest/",
    "Vercel": "https://vercel.com/docs/rest-api/",
    "Netlify": "https://docs.netlify.com/api/get-started/",
    "Cloudflare": "https://developers.cloudflare.com/api/",
    "Supabase": "https://supabase.com/docs/reference/",
    "Neo4j": "https://neo4j.com/docs/http-api/current/",
    "Snowflake": "https://docs.snowflake.com/en/developer-guide/sql-api/index",
    "MongoDB Atlas": "https://www.mongodb.com/docs/atlas/",
    "Datadog": "https://docs.datadoghq.com/api/latest/",
    "Sentry": "https://docs.sentry.io/api/",
    "Notion": "https://developers.notion.com/reference/intro",
    "Airtable": "https://airtable.com/developers/web/api/introduction",
    "Linear": "https://linear.app/developers",
    "Jira": "https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/",
    "Asana": "https://developers.asana.com/docs",
    "Monday.com": "https://developer.monday.com/api-reference/docs",
    "ClickUp": "https://clickup.com/api",
    "Coda": "https://coda.io/developers/apis/v1",
    "Smartsheet": "https://developers.smartsheet.com/api/smartsheet/introduction",
    "Harvest": "https://harvestapp.com/api-v2",
    "Stripe": "https://docs.stripe.com/api",
    "Plaid": "https://plaid.com/docs/api/",
    "Binance": "https://developers.binance.com/docs/binance-spot-api-docs",
    "Paygent Connect": "https://www.paygent.co.jp/",
    "iPayX": "https://ipayx.com/",
    "QuickBooks": "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account",
    "Xero": "https://developer.xero.com/documentation/api/accounting/overview",
    "Brex": "https://developer.brex.com/",
    "Ramp": "https://docs.ramp.com/developer-api/",
    "PitchBook": "https://pitchbook.com/",
    "NotebookLM": "https://notebooklm.google.com/",
    "Otter AI": "https://otter.ai/",
    "Fathom": "https://fathom.video/",
    "Consensus": "https://consensus.app/",
    "Reducto": "https://docs.reducto.ai/",
    "Devin": "https://devin.ai/",
    "higgsfield": "https://higgsfield.ai/",
    "Mermaid CLI": "https://github.com/mermaid-js/mermaid-cli",
    "YouTube Transcript": "https://youtubetranscript.dev/",
    "Grain": "https://grain.com/",
}

ALIASES = {
    "Lark (Larksuite)": ["lark", "larksuite"], "Zoho Cliq": ["zoho cliq", "cliq"],
    "Meta Ads": ["meta", "facebook", "ads manager"], "LinkedIn Ads": ["linkedin", "campaign manager"],
    "Threads (Meta)": ["threads", "meta"], "Magento (Adobe Commerce)": ["magento", "adobe commerce"],
    "Amazon Selling Partner": ["amazon", "selling partner"], "QuickBooks": ["quickbooks", "intuit"],
    "Jira": ["jira", "atlassian"], "NotebookLM": ["notebooklm", "google"],
    "Mermaid CLI": ["mermaid", "mermaid cli"], "YouTube Transcript": ["youtube transcript", "transcript"],
    "Paygent Connect": ["paygent", "paygent connect"], "iPayX": ["ipayx"],
}


class MainContentParser(HTMLParser):
    """Extract titles, meta description, body blocks, and links without scripts/nav."""
    EXCLUDED = {"script", "style", "svg", "noscript", "nav", "footer", "header", "form"}
    BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "td", "dd", "dt"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.title_mode = False
        self.title_parts: list[str] = []
        self.meta_description = ""
        self.blocks: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.active: list[str] = []
        self.active_tag: str | None = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in self.EXCLUDED:
            self.skip += 1
        if self.skip:
            return
        if tag == "title":
            self.title_mode = True
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.meta_description = attrs.get("content", "").strip()
        if tag == "a" and attrs.get("href"):
            self.links.append((attrs["href"], ""))
        if tag in self.BLOCKS:
            self.active_tag = tag
            self.active = []

    def handle_endtag(self, tag):
        if self.skip:
            if tag in self.EXCLUDED:
                self.skip -= 1
            return
        if tag == "title":
            self.title_mode = False
        if tag in self.BLOCKS and self.active_tag == tag:
            text = " ".join(" ".join(self.active).split())
            if text:
                self.blocks.append(text)
            self.active_tag = None
            self.active = []

    def handle_data(self, data):
        if self.skip:
            return
        data = " ".join(data.split())
        if not data:
            return
        if self.title_mode:
            self.title_parts.append(data)
        if self.active_tag:
            self.active.append(data)

    @property
    def title(self):
        return " ".join(self.title_parts).strip()


class PoliteFetcher:
    def __init__(self):
        self.robots: dict[str, tuple[bool, RobotFileParser | None]] = {}
        self.last_request: dict[str, float] = {}
        self.domain_locks: dict[str, threading.Lock] = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.5"})

    def delay(self, host: str):
        lock = self.domain_locks.setdefault(host, threading.Lock())
        with lock:
            wait = PER_HOST_DELAY - (time.monotonic() - self.last_request.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            self.last_request[host] = time.monotonic()

    def robots_allowed(self, url: str) -> tuple[bool, str]:
        parts = urlsplit(url)
        host = parts.netloc.lower()
        if host not in self.robots:
            robots_url = f"{parts.scheme}://{host}/robots.txt"
            self.delay(host)
            try:
                response = self.session.get(robots_url, timeout=TIMEOUT, allow_redirects=False)
            except requests.RequestException as exc:
                self.robots[host] = (False, None)
                return False, f"robots.txt request failed: {type(exc).__name__}"
            if response.status_code in (401, 403, 429) or response.status_code >= 500:
                self.robots[host] = (False, None)
                return False, f"robots.txt unavailable/restricted (HTTP {response.status_code}); fail closed"
            if response.status_code in (404, 410):
                self.robots[host] = (True, None)
            elif response.ok:
                parser = RobotFileParser(robots_url)
                parser.parse(response.text.splitlines())
                self.robots[host] = (True, parser)
            else:
                self.robots[host] = (False, None)
                return False, f"robots.txt returned HTTP {response.status_code}; fail closed"
        allowed, parser = self.robots[host]
        if not allowed:
            return False, "site robots policy could not be confirmed"
        if parser and not parser.can_fetch(USER_AGENT, url):
            return False, "disallowed by robots.txt"
        return True, "allowed by robots.txt or no robots file"

    def get(self, url: str) -> tuple[str | None, str, str]:
        current = url
        for redirect in range(4):
            allowed, reason = self.robots_allowed(current)
            if not allowed:
                return None, "blocked_robots", reason
            host = urlsplit(current).netloc.lower()
            response = None
            for attempt in range(1, 3):
                self.delay(host)
                try:
                    response = self.session.get(current, timeout=TIMEOUT, allow_redirects=False)
                except requests.RequestException as exc:
                    if attempt == 1:
                        time.sleep(1.0 + random.uniform(0.0, 0.5))
                        continue
                    return None, "error", f"request failed after one bounded retry: {type(exc).__name__}"
                if response.status_code >= 500 and attempt == 1:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        wait = min(10.0, max(0.0, float(retry_after))) if retry_after else 1.0 + random.uniform(0.0, 0.5)
                    except ValueError:
                        wait = 1.0 + random.uniform(0.0, 0.5)
                    time.sleep(wait)
                    continue
                break
            if response is None:
                return None, "error", "request failed without a response"
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    return None, "error", "redirect did not include a Location"
                current = urljoin(current, location)
                continue
            if response.status_code in (403, 429, 401, 402):
                label = "rate_limited" if response.status_code == 429 else "inaccessible"
                return None, label, f"HTTP {response.status_code}; not retried or bypassed"
            if response.status_code in (404, 410):
                return None, "not_found", f"HTTP {response.status_code}"
            if response.status_code >= 500:
                return None, "error", f"HTTP {response.status_code}; not retried"
            if not response.ok:
                return None, "error", f"HTTP {response.status_code}"
            content_type = response.headers.get("Content-Type", "").lower()
            if "html" not in content_type and "json" not in content_type and "text/" not in content_type:
                return None, "error", f"non-text content type: {content_type or 'unknown'}"
            return response.text[:2_000_000], "retrieved", response.url
        return None, "error", "too many redirects"


def parse_html(text: str) -> MainContentParser:
    parser = MainContentParser()
    try:
        parser.feed(text)
    except Exception:
        pass
    return parser


def app_matches(app_name: str, parser: MainContentParser, url: str) -> bool:
    haystack = " ".join([parser.title, parser.meta_description, *parser.blocks[:8]]).lower()
    aliases = ALIASES.get(app_name, [app_name.lower()])
    return any(alias and alias in haystack for alias in aliases)


def excerpt_for(parser: MainContentParser, patterns: tuple[str, ...], max_chars: int = 520) -> str | None:
    for block in parser.blocks:
        if len(block) > 35 and any(re.search(pattern, block, re.I) for pattern in patterns):
            if len(block) > max_chars:
                return block[:max_chars - 1].rsplit(" ", 1)[0] + "…"
            return block
    return None


def add_evidence(record: dict, *, field: str, claim: str, url: str, source_title: str, source_type: str, excerpt: str):
    quality, quality_note = classify_excerpt(excerpt)
    key = (field, claim, url)
    if any((e.get("field"), e.get("claim"), str(e.get("url"))) == key for e in record["evidence"]):
        return
    record["evidence"].append({
        "field": field, "claim": claim, "url": url, "source_type": source_type,
        "source_title": source_title or url, "excerpt": excerpt,
        "retrieval_status": "retrieved", "claim_supported": "unverified",
        "retrieval_note": None, "evidence_quality": quality,
        "evidence_quality_note": quality_note, "human_verdict": None, "review_method": None,
    })


def extract_from_page(app_name: str, record: dict, url: str, parser: MainContentParser):
    title = parser.title or url
    path = urlsplit(url).path.lower()
    if parser.meta_description and record["description"] == "unknown" and urlsplit(url).path.rstrip("/") == "":
        desc = parser.meta_description.strip()
        quality, _ = classify_excerpt(desc)
        if quality == "usable":
            record["description"] = desc
            add_evidence(record, field="description", claim=f"The public page describes {app_name} as: {desc}", url=url, source_title=title, source_type="public product page", excerpt=desc)

    doc_page = any(word in path + " " + title.lower() for word in ("developer", "api", "reference", "docs", "openapi", "swagger", "mcp"))
    if doc_page:
        api_excerpt = excerpt_for(parser, (r"REST API", r"RESTful", r"GraphQL API", r"OpenAPI", r"API reference"))
        api_quality = classify_excerpt(api_excerpt)[0] if api_excerpt else "insufficient"
        if api_excerpt and api_quality == "usable":
            has_rest = bool(re.search(r"REST\s*(?:API|endpoint|interface)|RESTful", api_excerpt, re.I))
            has_graphql = bool(re.search(r"GraphQL", api_excerpt, re.I))
            if has_rest and has_graphql:
                record["api_type"] = "both"
                proto = "The documentation describes REST and GraphQL API surfaces."
            elif has_rest:
                record["api_type"] = "REST"
                proto = "The documentation describes a REST API surface."
            elif has_graphql:
                record["api_type"] = "GraphQL"
                proto = "The documentation describes a GraphQL API surface."
            else:
                proto = "The documentation references an API surface; its protocol type is not explicit in this excerpt."
            if has_rest or has_graphql:
                add_evidence(record, field="api_type", claim=proto, url=url, source_title=title, source_type="API/developer documentation", excerpt=api_excerpt)
            if record["api_breadth"] == "unknown":
                record["api_breadth"] = api_excerpt
            add_evidence(record, field="api_breadth", claim=f"API documentation excerpt for {app_name} describes this surface: {api_excerpt}", url=url, source_title=title, source_type="API/developer documentation", excerpt=api_excerpt)

        auth_excerpt = excerpt_for(parser, (r"OAuth\s*2", r"API keys?", r"access tokens?", r"Bearer", r"Basic authentication", r"PKCE"))
        if auth_excerpt and classify_excerpt(auth_excerpt)[0] == "usable":
            methods = []
            for pattern, label in ((r"OAuth\s*2(?:\.0)?", "OAuth 2.0"), (r"API keys?", "API key"), (r"Bearer", "Bearer token"), (r"Basic authentication", "HTTP Basic authentication"), (r"PKCE", "PKCE")):
                if re.search(pattern, auth_excerpt, re.I) and label not in methods:
                    methods.append(label)
            record["auth_methods"] = sorted(set(record.get("auth_methods", []) + methods))
            add_evidence(record, field="auth_methods", claim=f"Authentication documentation states: {auth_excerpt}", url=url, source_title=title, source_type="authentication documentation", excerpt=auth_excerpt)

        mcp_excerpt = excerpt_for(parser, (r"Model Context Protocol", r"\bMCP server\b", r"MCP endpoint"))
        if mcp_excerpt and classify_excerpt(mcp_excerpt)[0] == "usable":
            record["mcp_status"] = f"A public page documents an MCP integration; scope is limited to the cited excerpt."
            add_evidence(record, field="mcp_status", claim=f"The page documents this MCP capability: {mcp_excerpt}", url=url, source_title=title, source_type="MCP documentation", excerpt=mcp_excerpt)

        blocker_excerpt = excerpt_for(parser, (r"rate limit", r"quota", r"permission", r"scope", r"plan required", r"administrator", r"contact sales", r"region"))
        if blocker_excerpt and classify_excerpt(blocker_excerpt)[0] == "usable":
            if not record["blockers"] or record["blockers"] == ["unknown"]:
                record["blockers"] = []
            if blocker_excerpt not in record["blockers"]:
                record["blockers"].append(blocker_excerpt)
            add_evidence(record, field="blockers", claim=f"The documentation states this access or usage qualification: {blocker_excerpt}", url=url, source_title=title, source_type="API/developer documentation", excerpt=blocker_excerpt)

    access_context = any(word in path + " " + title.lower() for word in ("pricing", "plan", "billing", "subscription"))
    if access_context:
        access_excerpt = excerpt_for(parser, (r"free", r"trial", r"\$\s?\d", r"per (?:user|seat|agent)", r"contact sales", r"plan"))
        if access_excerpt and classify_excerpt(access_excerpt)[0] == "usable":
            record["access_model"] = access_excerpt
            add_evidence(record, field="access_model", claim=f"The pricing/access page states: {access_excerpt}", url=url, source_title=title, source_type="pricing/access page", excerpt=access_excerpt)


def new_record(app: dict[str, str]) -> dict:
    return {
        "app_name": app["app_name"], "category": app["category"],
        "description": "unknown", "auth_methods": [], "access_model": "unknown",
        "api_type": "unknown", "api_breadth": "unknown", "mcp_status": "unknown",
        "buildability": "unclear", "blockers": [], "evidence": [],
        "confidence": "low", "last_checked": date.today().isoformat(),
        "research_status": "not_researched", "research_note": None,
        "source_attempts": [], "source_queue": [],
    }


def save(output: Path, records: list[dict]):
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(output)


def prepare_record(app: dict[str, str], record: dict | None) -> dict:
    if record:
        # Revalidate saved data while preserving existing human-verification fields.
        parsed = AppResearchRecord.model_validate(record).model_dump(mode="json")
        return parsed
    record = new_record(app)
    seed = SITE_URLS.get(app["app_name"])
    if seed:
        record["source_queue"].append(seed)
    else:
        record["research_note"] = "No candidate site URL is mapped; no external source was assumed."
    return record


def source_type_for(url: str) -> str:
    path = urlsplit(url).path.lower()
    if "mcp" in path:
        return "MCP documentation"
    if any(key in path for key in ("pricing", "plan", "billing")):
        return "pricing/access page"
    if any(key in path for key in ("developer", "api", "docs", "reference", "openapi", "swagger")):
        return "API/developer documentation"
    return "public product page"


def process_app(app: dict[str, str], record: dict, fetcher: PoliteFetcher, records: list[dict], index: int, output: Path):
    attempted = {str(item["url"]) for item in record.get("source_attempts", [])}
    seed = SITE_URLS.get(app["app_name"])
    if seed and seed not in record.get("source_queue", []) and seed not in attempted:
        record["source_queue"].append(seed)
    pages_done = 0
    while record["source_queue"] and pages_done < MAX_PAGES_PER_APP:
        url = str(record["source_queue"].pop(0))
        if url in attempted:
            continue
        content, status, note = fetcher.get(url)
        attempt = {"url": url, "status": status, "note": note if status != "retrieved" else None}
        record["source_attempts"].append(attempt)
        attempted.add(url)
        pages_done += 1
        if status == "retrieved" and content:
            parser = parse_html(content)
            if not app_matches(app["app_name"], parser, url):
                attempt["status"] = "error"
                attempt["note"] = "Page title/body did not identify the requested app; page content not used as evidence."
            else:
                extract_from_page(app["app_name"], record, url, parser)
                base_host = urlsplit(url).netloc.lower()
                links = []
                for href, _text in parser.links:
                    candidate = urljoin(url, html.unescape(href))
                    parts = urlsplit(candidate)
                    if parts.scheme not in ("http", "https") or parts.netloc.lower() == base_host:
                        if re.search(r"docs|developer|api|reference|openapi|swagger|mcp|pricing|plans|billing|auth", parts.path, re.I):
                            if candidate not in record["source_queue"] and candidate not in attempted and candidate not in links:
                                links.append(candidate)
                record["source_queue"].extend(links[:8])
                record["research_status"] = "partial" if record["evidence"] else "not_researched"
                record["research_note"] = "Free public-page extraction only; all extracted claims remain unverified."
        else:
            record["research_note"] = f"Latest public source attempt: {status} ({note})."
        # Persist after each URL so interruption never loses completed work.
        records[index] = record
        save(output, records)

    evidence_fields = {item.get("field") for item in record["evidence"] if item.get("claim_supported") == "unverified" and item.get("evidence_quality") == "usable"}
    if {"api_type", "auth_methods", "access_model", "api_breadth"}.issubset(evidence_fields):
        record["research_status"] = "researched"
        record["confidence"] = "medium"
    elif record["evidence"]:
        record["research_status"] = "partial"
    elif record["source_attempts"] and all(a["status"] in {"blocked_robots", "inaccessible", "rate_limited", "not_found", "error"} for a in record["source_attempts"]):
        record["research_status"] = "blocked"
    else:
        record["research_status"] = "not_researched"
    record["last_checked"] = date.today().isoformat()
    records[index] = record
    save(output, records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Free, polite extraction from public app pages; no API key or Firecrawl.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum new apps to attempt; default processes every remaining assignment app.")
    parser.add_argument("--output", default=str(OUTPUT), help="Separate resumable output; existing v2 is read-only.")
    parser.add_argument("--max-pages-per-app", type=int, default=MAX_PAGES_PER_APP)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.max_pages_per_app < 1 or args.max_pages_per_app > 10:
        parser.error("--max-pages-per-app must be between 1 and 10")
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    with (PROJECT_ROOT / "data" / "apps.csv").open("r", encoding="utf-8-sig", newline="") as f:
        apps = list(csv.DictReader(f))
    if output.exists():
        records = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("Output must be a JSON list")
    else:
        # Copy existing v2 records byte-for-byte at the object level; do not
        # enrich/rewrite their 15 separate human-supported evidence entries.
        records = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
        save(output, records)
    by_name = {r["app_name"].casefold(): i for i, r in enumerate(records)}
    baseline_names = {r["app_name"].casefold() for r in json.loads(BASELINE_V2.read_text(encoding="utf-8"))}
    resumed = []
    for app in apps:
        key = app["app_name"].casefold()
        if key in by_name and key not in baseline_names:
            record = records[by_name[key]]
            attempted_urls = {str(a["url"]) for a in record.get("source_attempts", [])}
            if any(str(url) not in attempted_urls for url in record.get("source_queue", [])):
                resumed.append((app, record, by_name[key]))
    missing = [app for app in apps if app["app_name"].casefold() not in by_name]
    if args.limit is not None:
        missing = missing[:args.limit]
    tasks = resumed + [(app, prepare_record(app, None), -1) for app in missing]
    if not tasks:
        print("No missing assignment apps to process.")
        return 0
    fetcher = PoliteFetcher()
    print(f"Queued {len(resumed)} apps to resume and {len(missing)} new apps. One request at a time; {PER_HOST_DELAY:.1f}s per host; robots enforced; no Firecrawl/API key.")
    for position, (app, record, index) in enumerate(tasks, 1):
        if index < 0:
            records.append(record)
            index = len(records) - 1
            by_name[app["app_name"].casefold()] = index
            save(output, records)
        print(f"[{position}/{len(missing)}] {app['app_name']}")
        process_app(app, record, fetcher, records, index, output)
        print(f"  status={record['research_status']}; evidence={len(record['evidence'])}; page_attempts={len(record['source_attempts'])}")
    for record in records:
        AppResearchRecord.model_validate(record)
    print(f"Saved {len(records)} records to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
