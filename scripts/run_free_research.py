"""Polite, no-key research pass over public app sites (no paid services).

The script uses only official-site URL seeds plus links found on those pages.
It never submits login forms, solves challenges, bypasses robots, or retries 403/429.
Results are saved after every page and can be resumed without refetching attempted
URLs. Search-result pages are not scraped; unknowns stay unknown.
"""

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import threading
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from appscout.evidence_quality import classify_excerpt
from appscout.models import AppResearchRecord
from appscout.scrapedo_client import ScrapeDoError, ScrapeDoHTTPError, fetch_page, get_token, scrape_do_diagnostics

APP_LIST = PROJECT_ROOT / "data" / "apps.csv"
BASELINE_V2 = PROJECT_ROOT / "output" / "research_results_v2.json"
OUTPUT = PROJECT_ROOT / "output" / "research_results_free.json"
USER_AGENT = "AppScoutTakeHomeResearch/1.0 (polite public documentation reader)"
PER_HOST_DELAY = 1.0
MAX_PAGES_PER_APP = 5
TIMEOUT = (8, 18)
CACHE_DIR = PROJECT_ROOT / "output" / "scrapedo_cache"
DEFAULT_CREDIT_CAP = 150

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
    # The docs.stripe.com API page was explicitly blocked by Scrape.do. This
    # alternate is Stripe's official SDK repository; do not retry that page.
    "Stripe": "https://github.com/stripe/stripe-python",
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

BLOCKED_SOURCE_LIMITATIONS = {
    "Stripe": (
        "https://docs.stripe.com/api",
        "Scrape.do returned HTTP 400 and explicitly disallowed this target during the user-reported smoke test; do not retry it.",
    ),
}


class ResearchBudgetReached(RuntimeError):
    """Raised before a Scrape.do request when this run's budget is exhausted."""


def scrapedo_attempted(record: dict) -> set[str]:
    """Only skip URLs already attempted through Scrape.do, not the old direct fetcher."""
    return {
        str(item["url"])
        for item in record.get("source_attempts", [])
        if str(item.get("note") or "").startswith("Scrape.do:")
        and "retrying once with Markdown" not in str(item.get("note") or "")
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
    def __init__(self, render: bool = False, credit_cap: float = DEFAULT_CREDIT_CAP,
                 max_requests: int = 100, ledger_path: Path | None = None):
        self.render = render
        self.credit_cap = credit_cap
        self.max_requests = max_requests
        self.ledger_path = ledger_path or (PROJECT_ROOT / "output" / "scrapedo_run_ledger.json")
        if self.ledger_path.exists():
            self.ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        else:
            self.ledger = {"credits_spent": 0.0, "requests_made": 0,
                           "reported_credits_spent": 0.0,
                           "unknown_cost_requests": 0, "last_remaining_credits": None,
                           "calls": []}
        self.ledger.setdefault("calls", [])
        self.ledger.setdefault("credits_spent", 0.0)
        self.ledger.setdefault("requests_made", 0)
        self.ledger.setdefault("unknown_cost_requests", 0)
        self.ledger.setdefault("reported_credits_spent", 0.0)
        self.ledger.setdefault("last_remaining_credits", None)
        self.ledger["credit_cap"] = credit_cap
        self.ledger["max_requests"] = max_requests
        self.robots: dict[str, tuple[bool, RobotFileParser | None]] = {}
        self.last_request: dict[str, float] = {}
        self.domain_locks: dict[str, threading.Lock] = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.5"})

    def save_ledger(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ledger_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.ledger_path)

    def ensure_budget(self):
        if self.ledger["requests_made"] >= self.max_requests:
            raise ResearchBudgetReached(f"request cap {self.max_requests} reached")
        if self.ledger["credits_spent"] + 1 > self.credit_cap:
            raise ResearchBudgetReached(f"credit cap {self.credit_cap:g} reached")

    def record_api_call(self, url: str, outcome: str, diagnostics: dict):
        cost_text = diagnostics.get("request_cost")
        try:
            cost = float(cost_text) if cost_text is not None else None
        except (TypeError, ValueError):
            cost = None
        # If the service omits the cost header, reserve one credit so that an
        # unreported request cannot silently make the batch appear free.
        charged = cost if cost is not None and cost >= 0 else 1.0
        if cost is None:
            self.ledger["unknown_cost_requests"] += 1
        else:
            self.ledger["reported_credits_spent"] = round(
                self.ledger["reported_credits_spent"] + cost, 4
            )
        self.ledger["credits_spent"] = round(self.ledger["credits_spent"] + charged, 4)
        remaining = diagnostics.get("remaining_credits")
        if remaining is not None:
            self.ledger["last_remaining_credits"] = remaining
        self.ledger["requests_made"] += 1
        self.ledger["calls"].append({"url": url, "outcome": outcome,
                                     "request_cost": cost_text,
                                     "conservative_charge": charged,
                                     "remaining_credits": remaining})
        self.save_ledger()

    def cache_path(self, url: str) -> Path:
        key = hashlib.sha256(f"{url}\nrender={self.render}\noutput=markdown".encode("utf-8")).hexdigest()
        return CACHE_DIR / f"{key}.json"

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
        allowed, reason = self.robots_allowed(url)
        if not allowed:
            return None, "blocked_robots", reason

        cache_file = self.cache_path(url)
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                content = cached.get("content")
                if isinstance(content, str) and content:
                    return content, "retrieved", "loaded successful response from local URL cache"
            except (OSError, ValueError, AttributeError):
                pass

        # Scrape.do is the network endpoint for each page fetch, so pace by
        # that host even when target domains differ.
        self.delay("api.scrape.do")
        self.ensure_budget()
        try:
            response = fetch_page(url, render=self.render, output="markdown")
        except ScrapeDoHTTPError as exc:
            self.record_api_call(url, f"HTTP {exc.status_code}", {
                "request_cost": exc.request_cost,
                "remaining_credits": exc.remaining_credits,
            })
            cost = exc.request_cost if exc.request_cost is not None else "unknown"
            balance = exc.remaining_credits if exc.remaining_credits is not None else "unknown"
            if exc.status_code == 429:
                return None, "rate_limited", f"HTTP 429; not retried; request cost={cost}; remaining credits={balance}"
            if exc.status_code in (401, 402, 403):
                return None, "inaccessible", f"HTTP {exc.status_code}; not retried; request cost={cost}; remaining credits={balance}"
            if exc.status_code in (404, 410):
                return None, "not_found", f"HTTP {exc.status_code}; request cost={cost}; remaining credits={balance}"
            if exc.status_code == 400 and url.rstrip("/") == "https://docs.stripe.com/api":
                return None, "error", f"HTTP 400; Scrape.do explicitly disallowed this target; URL not retried; request cost={cost}; remaining credits={balance}"
            if exc.status_code == 400:
                detail = exc.diagnostic_body[:220] if exc.diagnostic_body else "no response detail"
                return None, "error", f"HTTP 400; {detail}; URL not retried; request cost={cost}; remaining credits={balance}"
            return None, "error", f"Scrape.do returned HTTP {exc.status_code}"
        except ScrapeDoError as exc:
            self.record_api_call(url, str(exc), {"request_cost": None, "remaining_credits": None})
            return None, "error", str(exc)

        content = response.text[:2_000_000]
        if not content.strip():
            self.record_api_call(url, "empty response", scrape_do_diagnostics(response.headers))
            return None, "error", "Scrape.do returned an empty page body"
        diagnostics = scrape_do_diagnostics(response.headers)
        self.record_api_call(url, f"HTTP {response.status_code}", diagnostics)
        cost = diagnostics["request_cost"] if diagnostics["request_cost"] is not None else "unknown"
        balance = diagnostics["remaining_credits"] if diagnostics["remaining_credits"] is not None else "unknown"
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = cache_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"url": url, "render": self.render, "content": content}, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cache_file)
        return content, "retrieved", f"HTTP {response.status_code}; request cost={cost}; remaining credits={balance}"


def parse_html(text: str) -> MainContentParser:
    parser = MainContentParser()
    try:
        parser.feed(text)
    except Exception:
        pass
    return parser


def parse_markdown(text: str) -> MainContentParser:
    """Adapt Scrape.do Markdown into the same light parser shape used by extraction."""
    parser = MainContentParser()
    blocks: list[str] = []
    current: list[str] = []
    in_code = False
    title_set = False
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    for line in text.splitlines():
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", line)
        if heading and not title_set:
            parser.title_parts.append(re.sub(r"[*_`]", "", heading.group(1)).strip())
            title_set = True
        if not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line.strip())
        for match in link_pattern.finditer(line):
            parser.links.append((match.group(2).strip("<>"), match.group(1)))
    if current:
        blocks.append("\n".join(current).strip())
    parser.blocks = [block for block in blocks if block]
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


def process_app(app: dict[str, str], record: dict, fetcher: PoliteFetcher, records: list[dict], index: int, output: Path, max_pages: int = MAX_PAGES_PER_APP) -> bool:
    attempted = scrapedo_attempted(record)
    seed = SITE_URLS.get(app["app_name"])
    if seed and seed not in record.get("source_queue", []) and seed not in attempted:
        if app["app_name"] in BLOCKED_SOURCE_LIMITATIONS:
            record["source_queue"].insert(0, seed)
        else:
            record["source_queue"].append(seed)
    pages_done = 0
    while record["source_queue"] and pages_done < max_pages:
        url = urldefrag(str(record["source_queue"].pop(0)))[0]
        if url in attempted:
            continue
        try:
            content, status, note = fetcher.get(url)
        except ResearchBudgetReached as exc:
            record["source_queue"].insert(0, url)
            records[index] = record
            save(output, records)
            print(f"Budget stop: {exc}; current app and remaining queue saved.")
            return False
        attempt = {"url": url, "status": status,
                   "note": f"Scrape.do: {note}" if note else "Scrape.do: request completed"}
        record["source_attempts"].append(attempt)
        attempted.add(url)
        pages_done += 1
        if status == "retrieved" and content:
            parser = parse_markdown(content)
            if not app_matches(app["app_name"], parser, url):
                attempt["status"] = "error"
                attempt["note"] = "Scrape.do: page title/body did not identify the requested app; page content not used as evidence."
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
                record["research_note"] = "Scrape.do public-page extraction; all extracted claims remain unverified."
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
    return True


def record_known_access_limitations(records: list[dict], baseline_names: set[str], output: Path):
    """Store the user-reported Stripe block without retrying the blocked URL."""
    for record in records:
        app_name = record.get("app_name")
        if str(app_name).casefold() in baseline_names or app_name not in BLOCKED_SOURCE_LIMITATIONS:
            continue
        blocked_url, explanation = BLOCKED_SOURCE_LIMITATIONS[app_name]
        record["source_queue"] = [
            item for item in record.get("source_queue", [])
            if str(item).rstrip("/") != blocked_url.rstrip("/")
        ]
        already_noted = any(
            str(item.get("url", "")).rstrip("/") == blocked_url.rstrip("/")
            and "explicitly disallowed" in str(item.get("note") or "")
            for item in record.get("source_attempts", [])
        )
        if not already_noted:
            record.setdefault("source_attempts", []).append({
                "url": blocked_url,
                "status": "error",
                "note": f"Scrape.do: {explanation}",
            })
        alternate = SITE_URLS.get(app_name)
        if alternate:
            record["source_queue"] = [item for item in record["source_queue"] if str(item) != alternate]
            record["source_queue"].insert(0, alternate)
    save(output, records)


def reschedule_html_parameter_failures(records: list[dict], baseline_names: set[str], output: Path):
    """Retry only prior generic HTML-output 400s once using Markdown output."""
    explicitly_blocked = {
        url.rstrip("/") for url, _ in BLOCKED_SOURCE_LIMITATIONS.values()
    }
    for record in records:
        if str(record.get("app_name", "")).casefold() in baseline_names:
            continue
        for attempt in record.get("source_attempts", []):
            url = str(attempt.get("url", ""))
            note = str(attempt.get("note") or "")
            if (url.rstrip("/") in explicitly_blocked
                    or note != "Scrape.do: Scrape.do returned HTTP 400"):
                continue
            attempt["note"] = (
                "Scrape.do: prior output=html request returned HTTP 400; "
                "retrying once with Markdown output after parameter correction."
            )
            record["source_queue"] = [item for item in record.get("source_queue", []) if str(item) != url]
            record["source_queue"].insert(0, url)
            break
    save(output, records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Polite public-page research through Scrape.do; calls are made only when this script is run.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum non-baseline apps to process in this run.")
    parser.add_argument("--output", default=str(OUTPUT), help="Separate resumable output; existing v2 is read-only.")
    parser.add_argument("--max-pages-per-app", type=int, default=MAX_PAGES_PER_APP)
    parser.add_argument("--max-credits", type=float, default=DEFAULT_CREDIT_CAP, help="Credit cap for this run and its persistent ledger (maximum 150).")
    parser.add_argument("--max-requests", type=int, default=100, help="Hard maximum Scrape.do calls for this output ledger (maximum 150).")
    parser.add_argument("--skip-app", action="append", default=[], help="Skip an app name; may be supplied more than once.")
    parser.add_argument("--include-app", action="append", default=[], help="Only process this app name; may be supplied more than once.")
    parser.add_argument("--ledger", default=None, help="Optional separate credit ledger path for a bounded continuation run.")
    parser.add_argument("--render", action="store_true", help="Request JavaScript rendering for this run; may use more Scrape.do credits.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.max_pages_per_app < 1 or args.max_pages_per_app > 10:
        parser.error("--max-pages-per-app must be between 1 and 10")
    if not 0 < args.max_credits <= DEFAULT_CREDIT_CAP:
        parser.error("--max-credits must be positive and no greater than 150")
    if not 1 <= args.max_requests <= DEFAULT_CREDIT_CAP:
        parser.error("--max-requests must be between 1 and 150")
    try:
        get_token()
    except ScrapeDoError as exc:
        print(f"ERROR: {exc}")
        return 2
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    ledger_path = Path(args.ledger) if args.ledger else output.with_name(f"{output.stem}_budget.json")
    if not ledger_path.is_absolute():
        ledger_path = PROJECT_ROOT / ledger_path
    fetcher = PoliteFetcher(render=args.render, credit_cap=args.max_credits,
                            max_requests=args.max_requests, ledger_path=ledger_path)
    with (PROJECT_ROOT / "data" / "apps.csv").open("r", encoding="utf-8-sig", newline="") as f:
        apps = list(csv.DictReader(f))
    if output.exists():
        records = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("Output must be a JSON list")
    else:
        # New outputs begin with the baseline if the caller has not supplied
        # an existing full-list copy. Existing records are never discarded.
        records = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
        save(output, records)
    by_name = {r["app_name"].casefold(): i for i, r in enumerate(records)}
    baseline_names = {r["app_name"].casefold() for r in json.loads(BASELINE_V2.read_text(encoding="utf-8"))}
    record_known_access_limitations(records, baseline_names, output)
    reschedule_html_parameter_failures(records, baseline_names, output)
    resumed = []
    for app in apps:
        key = app["app_name"].casefold()
        if key in by_name and key not in baseline_names:
            record = records[by_name[key]]
            attempted_urls = scrapedo_attempted(record)
            seed = SITE_URLS.get(app["app_name"])
            pending_queue = any(str(url) not in attempted_urls for url in record.get("source_queue", []))
            pending_seed = bool(seed and seed not in attempted_urls)
            if pending_queue or pending_seed:
                resumed.append((app, record, by_name[key]))
    missing = [app for app in apps if app["app_name"].casefold() not in by_name]
    tasks = resumed + [(app, prepare_record(app, None), -1) for app in missing]
    skip_apps = {name.casefold() for name in args.skip_app}
    tasks = [task for task in tasks if task[0]["app_name"].casefold() not in skip_apps]
    include_apps = {name.casefold() for name in args.include_app}
    if include_apps:
        known_apps = {row["app_name"].casefold() for row in apps}
        unknown = include_apps - known_apps
        if unknown:
            parser.error(f"unknown --include-app value(s): {', '.join(sorted(unknown))}")
        tasks = [task for task in tasks if task[0]["app_name"].casefold() in include_apps]
    if args.limit is not None:
        tasks = tasks[:args.limit]
    if not tasks:
        print("No missing assignment apps to process.")
        return 0
    render_label = "enabled" if args.render else "disabled"
    print(f"Queued {len(tasks)} apps. Credit cap={args.max_credits:g}; request cap={args.max_requests}; already spent={fetcher.ledger['credits_spent']:g}; rendering {render_label}; cache and output are resumable.")
    completed_apps = []
    stopped_for_budget = False
    for position, (app, record, index) in enumerate(tasks, 1):
        if index < 0:
            records.append(record)
            index = len(records) - 1
            by_name[app["app_name"].casefold()] = index
            save(output, records)
        print(f"[{position}/{len(tasks)}] {app['app_name']}")
        if app["app_name"] == "YouTube Transcript":
            # Avoid a public sign-up route; prioritize the official API docs.
            record["source_queue"] = [
                item for item in record.get("source_queue", [])
                if not re.search(r"/(?:auth/)?sign[-_]up(?:/|\?|$)", str(item), re.I)
            ]
            api_docs = "https://youtubetranscript.dev/api-docs"
            record["source_queue"] = [item for item in record["source_queue"] if urldefrag(str(item))[0] != api_docs]
            record["source_queue"].insert(0, api_docs)
            records[index] = record
            save(output, records)
        continued = process_app(app, record, fetcher, records, index, output, args.max_pages_per_app)
        if not continued:
            stopped_for_budget = True
            break
        if any(str(item.get("note") or "").startswith("Scrape.do:") for item in record.get("source_attempts", [])):
            completed_apps.append(app["app_name"])
        print(f"  status={record['research_status']}; evidence={len(record['evidence'])}; page_attempts={len(record['source_attempts'])}")
    for record in records:
        AppResearchRecord.model_validate(record)
    print(f"Saved {len(records)} records to {output}")
    print(f"Scrape.do calls={fetcher.ledger['requests_made']}; request-cost headers sum={fetcher.ledger['reported_credits_spent']:g}; conservative budget charges={fetcher.ledger['credits_spent']:g}; unknown-cost calls={fetcher.ledger['unknown_cost_requests']}.")
    print(f"Apps with a Scrape.do attempt this run={len(set(completed_apps))}; queued apps remaining={max(0, len(tasks) - len(set(completed_apps)))}.")
    if stopped_for_budget:
        print("Stopped at budget cap; rerunning with the same output resumes from the saved queues and cache.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
