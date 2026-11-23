"""Build the self-contained all-app report from local project data only."""

import csv
import html
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from appscout.analytics import analyze
from appscout.evidence_quality import classify_excerpt
from appscout.models import AppResearchRecord

FIELDS = ["description", "auth_methods", "access_model", "api_type", "api_breadth", "mcp_status", "buildability", "blockers"]


def e(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def chart(counter: Counter, total=None) -> str:
    if not counter:
        return '<p class="muted">No stored data for this view.</p>'
    max_value = max(counter.values()) or 1
    parts = []
    for name, value in counter.most_common():
        width = max(2, round(value / max_value * 100))
        amount = f"{value}/{total}" if total is not None else str(value)
        parts.append(f'<div class="bar"><div class="bar-label"><b>{e(name)}</b><span>{amount}</span></div><div class="track"><i style="width:{width}%"></i></div></div>')
    return "".join(parts)


def status_for(record: dict) -> str:
    explicit = record.get("research_status")
    if explicit:
        return explicit
    return "researched" if record.get("evidence") else "not_researched"


def quality_for(ev: dict) -> tuple[str, str]:
    if ev.get("excerpt") and not ev.get("evidence_quality"):
        return classify_excerpt(ev["excerpt"])
    return ev.get("evidence_quality", "insufficient"), ev.get("evidence_quality_note") or "No excerpt is stored."


def field_status(record: dict, field: str) -> str:
    value = record.get(field)
    valtext = " ".join(value) if isinstance(value, list) else str(value or "")
    if any(word in valtext.lower() for word in ("unknown", "unclear", "not established")):
        return "Explicitly unknown / unclear"
    matches = [x for x in record.get("evidence", []) if x.get("field") == field]
    if matches:
        if any(x.get("human_verdict") == "supported" for x in matches):
            return "A sampled claim was human-supported"
        if any(x.get("excerpt") and quality_for(x)[0] == "usable" for x in matches):
            return "Excerpt available; claim unverified"
        return "Mapped source, excerpt weak or unavailable"
    if status_for(record) in {"blocked", "not_researched"}:
        return "Not established in this pass"
    return "No field-linked evidence"


def record_row(record: dict) -> str:
    app = record["app_name"]
    status = status_for(record)
    auth = "; ".join(record.get("auth_methods", [])) or "unknown / no methods recorded"
    blockers = "".join(f"<li>{e(x)}</li>" for x in record.get("blockers", [])) or '<li class="muted">No blocker detail recorded.</li>'
    field_rows = "".join(f'<li><code>{e(field)}</code><span>{e(field_status(record, field))}</span></li>' for field in FIELDS)
    evidence_rows = []
    for ev in record.get("evidence", []):
        q, reason = quality_for(ev)
        title = ev.get("source_title") or ev.get("url", "Source")
        verdict = ev.get("human_verdict") or "not reviewed"
        excerpt = ev.get("excerpt") or ev.get("retrieval_note") or ev.get("evidence_quality_note") or "No excerpt available."
        evidence_rows.append(
            f'<li class="evidence"><a href="{e(ev.get("url", ""))}" target="_blank" rel="noopener noreferrer">{e(title)} ↗</a>'
            f'<p><b>{e(ev.get("field") or "Field not mapped")}</b> · {e(ev.get("claim", ""))}</p>'
            f'<blockquote>{e(excerpt)}</blockquote><div class="pills"><span class="pill q-{e(q)}">Excerpt: {e(q)}</span>'
            f'<span class="pill">Retrieval: {e(ev.get("retrieval_status", "not_attempted"))}</span>'
            f'<span class="pill">Automated: {e(ev.get("claim_supported", "unverified"))}</span>'
            f'<span class="pill {"human" if ev.get("human_verdict") else ""}">Human: {e(verdict)}</span></div>'
            f'<small>{e(reason)}</small></li>'
        )
    attempts = "".join(f'<li><a href="{e(a.get("url", ""))}" target="_blank" rel="noopener noreferrer">{e(a.get("url", ""))}</a> — {e(a.get("status", ""))}{(": " + e(a.get("note"))) if a.get("note") else ""}</li>' for a in record.get("source_attempts", []))
    if not attempts:
        attempts = '<li class="muted">No free-source attempt log for this record.</li>'
    detail = "".join(evidence_rows) or '<li class="muted">No claim-level evidence was collected.</li>'
    search = " ".join([app, record.get("category", ""), record.get("description", ""), record.get("access_model", ""), record.get("api_type", ""), record.get("api_breadth", ""), record.get("mcp_status", ""), auth, *record.get("blockers", [])])
    status_class = status.replace("_", "-")
    return (
        f'<tr data-category="{e(record.get("category", ""))}" data-build="{e(record.get("buildability", "unclear"))}" data-status="{e(status)}" data-search="{e(search)}">'
        f'<td><strong>{e(app)}</strong><small>{e(record.get("description", "unknown"))}</small></td>'
        f'<td>{e(record.get("category", ""))}</td><td><span class="status {e(status_class)}">{e(status.replace("_", " "))}</span></td>'
        f'<td><details><summary>View 8 fields</summary><ul class="field-states">{field_rows}</ul></details></td>'
        f'<td><span class="verdict v-{e(record.get("buildability", "unclear"))}">{e(record.get("buildability", "unclear").replace("_", " "))}</span></td>'
        f'<td>{e(record.get("api_type", "unknown"))}<small>{e(record.get("api_breadth", "unknown"))}</small></td>'
        f'<td>{e(auth)}</td><td>{e(record.get("access_model", "unknown"))}</td><td>{e(record.get("mcp_status", "unknown"))}</td>'
        f'<td><details><summary>{len(record.get("blockers", []))} blockers</summary><ul>{blockers}</ul></details></td>'
        f'<td><details><summary>{len(evidence_rows)} evidence · {len(record.get("source_attempts", []))} attempts</summary><ul class="evidence-list">{detail}</ul><h4>Source attempts</h4><ul>{attempts}</ul></details></td></tr>'
    )


def make_html(records: list[dict], apps: list[dict], metrics: dict, reviewed: list[dict]) -> str:
    rows = "".join(record_row(r) for r in records)
    category_html = "".join(
        f'<div class="bar"><div class="bar-label"><b>{e(x["category"])}</b><span>{x["researched"]} / {x["total"]}</span></div><div class="track"><i style="width:{round(x["researched"] / x["total"] * 100) if x["total"] else 0}%"></i></div></div>'
        for x in metrics["category_coverage"]
    )
    categories = "".join(f'<option>{e(x)}</option>' for x in sorted({r["category"] for r in records}))
    statuses = "".join(f'<option value="{e(x)}">{e(x.replace("_", " "))}</option>' for x in ("researched", "partial", "blocked", "not_researched"))
    human_apps = ", ".join(sorted({x["app_name"] for x in reviewed}))
    total = metrics["assignment_total"]
    usable_apps = metrics["apps_with_usable_evidence"]
    evidence_count = metrics["evidence_total"]
    human_supported = sum(1 for x in reviewed if x.get("human_verdict") == "supported")
    partial = metrics["partial_total"]
    blocked = metrics["blocked_total"]
    not_researched = metrics["not_researched_total"]
    record_count = metrics["record_total"]
    latest = max((r.get("last_checked", "") for r in records), default="not recorded")
    unknowns = "".join(f'<li><b>{n}</b> records explicitly mark <code>{e(f)}</code> unknown/unclear.</li>' for f,n in metrics["unknown_fields"].most_common()) or '<li>No explicit unknown marker found in a required text field. An empty field or missing evidence still remains unresolved.</li>'
    field_status_html = "".join(f'<div class="field-summary"><b>{e(field)}</b><div>{" · ".join(f"{e(state)}: {count}" for state,count in counter.most_common())}</div></div>' for field,counter in metrics["field_status"].items())
    attempts = metrics["source_attempt_status"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="AppScout's source-linked assessment of software integration readiness for AI agents."><title>AppScout | 100 App Integration Readiness</title>
<style>
:root{{--ink:#172b3a;--muted:#61727e;--paper:#f6f4ee;--card:#fffefa;--line:#dce3df;--green:#126b55;--mint:#daf1e5;--blue:#3a7181;--gold:#e5aa4f;--red:#aa5648;--shadow:0 14px 36px rgba(24,51,62,.08)}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}}a{{color:#075f58;text-decoration-thickness:1px;text-underline-offset:3px}}a:hover{{color:#9d591b}}.wrap{{max-width:1380px;margin:auto;padding:0 26px}}.top{{height:64px;border-bottom:1px solid var(--line);background:#fbfaf6}}.top .wrap{{height:100%;display:flex;align-items:center;justify-content:space-between}}.logo{{font-size:18px;font-weight:900;letter-spacing:-.05em}}.logo i{{color:var(--green);font-style:normal}}nav{{display:flex;gap:19px;font-size:13px}}nav a{{text-decoration:none;color:var(--muted)}}.tag{{background:var(--mint);color:var(--green);padding:5px 9px;border-radius:99px;font-size:10px;font-weight:850;letter-spacing:.06em}}.hero{{padding:66px 0 38px;background:radial-gradient(ellipse at 80% 15%,#e2f0e8,transparent 42%),linear-gradient(180deg,#fbfaf6,var(--paper))}}.eyebrow{{text-transform:uppercase;color:var(--green);letter-spacing:.14em;font-size:11px;font-weight:850}}h1{{font-size:clamp(42px,6.6vw,78px);line-height:.97;letter-spacing:-.065em;max-width:980px;margin:15px 0 20px}}h2{{font-size:31px;letter-spacing:-.045em;margin:4px 0 8px}}h3{{font-size:18px;margin:0 0 12px}}p{{margin:8px 0 12px}}.lede{{font-size:19px;max-width:820px;color:#455b64}}.notice{{max-width:980px;margin-top:28px;padding:16px 19px;background:#fff8e9;border:1px solid #e9cc92;border-left:5px solid var(--gold);border-radius:9px}}.notice b{{display:block}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0 52px}}.metric,.panel,.step,.vcard{{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}}.metric{{padding:19px}}.metric strong{{display:block;font-size:35px;letter-spacing:-.05em;line-height:1.1;color:var(--green)}}.metric span{{font-size:13px;color:var(--muted)}}section{{padding:37px 0;border-top:1px solid var(--line)}}.head{{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:22px}}.muted{{color:var(--muted)}}.small{{font-size:12px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.panel{{padding:22px}}.bars{{display:grid;gap:12px}}.bar-label{{display:flex;justify-content:space-between;gap:12px;font-size:13px;margin-bottom:4px}}.bar-label span{{color:var(--muted);white-space:nowrap}}.track{{height:8px;background:#e9efeb;border-radius:99px;overflow:hidden}}.track i{{display:block;height:100%;background:linear-gradient(90deg,var(--green),#58a78c);border-radius:inherit}}.coverage i{{background:linear-gradient(90deg,#427d8b,#84b7b6)}}.callout{{background:#eef6f1;border:1px solid #d5e9de;border-radius:10px;padding:16px;margin-top:14px}}.callout b{{color:var(--green)}}.clean{{padding-left:20px}}.clean li{{margin:6px 0}}.field-summary{{border-bottom:1px solid var(--line);padding:8px 0;font-size:13px}}.field-summary div{{color:var(--muted)}}.workflow{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.step{{padding:19px}}.step b{{color:var(--green);display:block;margin-bottom:8px}}.step p{{font-size:13px;color:var(--muted)}}.filters{{display:flex;gap:9px;flex-wrap:wrap;margin:17px 0}}input,select{{font:inherit;padding:10px 12px;border-radius:8px;border:1px solid #cbd6d1;background:white;color:var(--ink)}}input{{min-width:240px;flex:1}}.tablebox{{overflow:auto;border:1px solid var(--line);border-radius:13px;background:var(--card);box-shadow:var(--shadow)}}table{{border-collapse:collapse;width:100%;min-width:1580px;font-size:12px}}th{{position:sticky;top:0;background:#edf3ef;color:#425963;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.07em}}td,th{{padding:12px;border-bottom:1px solid #e7ece9;vertical-align:top}}td{{max-width:240px}}td small{{display:block;color:var(--muted);margin-top:5px;max-width:280px}}.status,.pill,.verdict{{display:inline-block;border-radius:99px;padding:4px 8px;font-size:10px;font-weight:800;white-space:nowrap;background:#edf0ee;color:#526269}}.researched{{background:#d9f0e2;color:#176044}}.partial{{background:#fff0d5;color:#84540d}}.blocked,.not-researched{{background:#f4e1df;color:#8e3d35}}.v-build_now{{background:#d9f0e2;color:#176044}}.v-build_with_restrictions{{background:#fff0d5;color:#84540d}}.v-needs_outreach{{background:#f9dedb;color:#8e3d35}}.v-unclear{{background:#e9e9e6;color:#555}}.q-usable{{background:#d9f0e2;color:#176044}}.q-navigation,.q-page_shell,.q-insufficient{{background:#fff0d5;color:#84540d}}.human{{background:#d9eafa;color:#245c83}}details summary{{cursor:pointer;color:#075f58;font-weight:750}}.field-states{{padding-left:0;min-width:270px}}.field-states li{{display:flex;justify-content:space-between;gap:10px;list-style:none;border-bottom:1px solid var(--line);padding:5px 0}}.field-states span{{color:var(--muted);text-align:right}}.evidence-list{{min-width:360px;max-width:720px;padding-left:20px}}.evidence{{list-style:none;padding:12px 0;border-bottom:1px solid var(--line)}}blockquote{{margin:8px 0;padding:10px 12px;background:#f1f6f2;border-left:3px solid #93c5af;color:#435963;font-size:12px}}.pills{{display:flex;gap:5px;flex-wrap:wrap}}.evidence small{{color:var(--muted)}}.vgrid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.vcard{{padding:18px}}.vcard b{{font-size:29px;display:block}}.footer{{padding:36px 0 52px;color:var(--muted);font-size:12px}}.none{{display:none;text-align:center;padding:20px;color:var(--muted)}}code{{background:#edf1ee;padding:2px 4px;border-radius:4px}}@media(max-width:850px){{.wrap{{padding:0 16px}}nav{{display:none}}.metrics{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}.workflow{{grid-template-columns:repeat(2,1fr)}}.vgrid{{grid-template-columns:repeat(2,1fr)}}.head{{display:block}}}}@media(max-width:450px){{.metrics{{gap:8px}}.metric{{padding:13px}}.metric strong{{font-size:27px}}.workflow{{grid-template-columns:1fr 1fr}}h2{{font-size:26px}}}}
</style></head><body><header class="top"><div class="wrap"><div class="logo">APP<i>SCOUT</i></div><nav><a href="#coverage">Coverage</a><a href="#patterns">Patterns</a><a href="#apps">100 apps</a><a href="#method">Method</a><a href="#verification">Review</a></nav><span class="tag">PUBLIC-SOURCE PASS · NO PAID API</span></div></header>
<main><div class="hero"><div class="wrap"><div class="eyebrow">Integration readiness · product operations</div><h1>Can an AI agent actually get in?</h1><p class="lede">A source-linked assessment of API access, authentication, plan gates, MCP surfaces, and implementation blockers across the 100-app assignment list.</p><div class="notice"><b>All 100 apps have a record, but this is not 100 completed research assessments.</b>{usable_apps} apps have at least one readable stored evidence excerpt. The remaining records are partial, blocked, or not researched at field level. The free pass used public pages only; Firecrawl credits were exhausted and no Firecrawl or paid API was called.</div></div></div>
<div class="wrap"><div class="metrics"><div class="metric"><strong>{record_count} / {total}</strong><span>assignment apps represented in the dataset</span></div><div class="metric"><strong>{usable_apps} / {total}</strong><span>apps with at least one readable excerpt</span></div><div class="metric"><strong>{metrics['evidence_total']}</strong><span>claim-level evidence records, with status shown</span></div><div class="metric"><strong>{human_supported} / {len(reviewed)}</strong><span>supported claims in the small manual sample</span></div></div></div>
<section id="coverage"><div class="wrap"><div class="head"><div><div class="eyebrow">01 · Coverage</div><h2>Coverage by assignment category</h2><p class="muted">An app counts as researched here only if it has at least one readable retrieved excerpt. This coverage measure says nothing about claim accuracy or field completeness.</p></div><a href="{e(apps[0].get('source_url',''))}" target="_blank" rel="noopener noreferrer">Assignment source ↗</a></div><div class="grid"><div class="panel"><h3>Apps with readable evidence</h3><div class="bars coverage">{category_html}</div></div><div class="panel"><h3>App-level research status</h3><div class="bars">{chart(Counter({"Researched (original evidence set)":sum(1 for r in records if status_for(r)=="researched"),"Partial with readable evidence":partial,"Blocked":blocked,"No usable evidence / not researched":not_researched}))}</div><div class="callout"><b>{usable_apps} apps have at least one usable excerpt.</b> More research may be needed even for those apps; each excerpt remains unverified unless a separate human verdict is shown.</div><p class="muted small">Source requests attempted in the free pass: {sum(attempts.values())}. Latest record date: {e(latest)}.</p></div></div></div></section>
<section id="patterns"><div class="wrap"><div class="head"><div><div class="eyebrow">02 · Patterns</div><h2>What the records say, and what they leave open</h2><p class="muted">App-level counts are drawn from stored field values. Auth/access/blocker groupings use transparent keyword rules and may overlap.</p></div><span class="tag">n = {record_count} records</span></div><div class="grid"><div class="panel"><h3>Buildability verdicts</h3>{chart(metrics['buildability'],record_count)}<p class="muted small">Agent/research judgments, not observed integration test outcomes.</p></div><div class="panel"><h3>API surface types</h3>{chart(metrics['api_surfaces'],record_count)}</div><div class="panel"><h3>Authentication families mentioned</h3>{chart(metrics['auth_families'])}<p class="muted small">An app can list several auth families. Empty method lists are not treated as proof that auth is unavailable.</p></div><div class="panel"><h3>Access characteristics mentioned</h3>{chart(metrics['access_characteristics'])}<p class="muted small">Overlapping groupings: paid plans and free trials can coexist.</p></div><div class="panel"><h3>Common blocker themes</h3>{chart(metrics['blocker_topics'],record_count)}<p class="muted small">Counts are apps whose stored blocker/access wording matches each theme.</p></div><div class="panel"><h3>Source retrieval outcomes</h3>{chart(attempts)}<p class="muted small">403, 429, 401 and robots restrictions were not bypassed or retried.</p></div></div><div class="panel" style="margin-top:16px"><h3>Field-level status across the list</h3>{field_status_html}<div class="callout"><b>Field completeness is unresolved.</b> A readable excerpt is not verification. The 15 reviewed claims cover five selected fields across three apps; they do not validate whole app records. Explicit unknowns, empty values, and fields without mapped evidence remain visible per app.</div></div><div class="grid" style="margin-top:16px"><div class="panel"><h3>Explicit unknowns</h3><ul class="clean">{unknowns}</ul></div><div class="panel"><h3>Evidence hygiene</h3>{chart(metrics['evidence_quality'])}<p class="muted small">The local classifier checks readability only. It does not decide whether an excerpt supports a claim.</p><ul class="clean"><li>{metrics['evidence_missing_title']} evidence records lack a source title.</li><li>{metrics['evidence_missing_field']} evidence records lack an explicit evidence-field mapping.</li><li>{metrics['evidence_missing_excerpt']} evidence records lack an excerpt.</li></ul></div></div></div></section>
<section id="apps"><div class="wrap"><div class="head"><div><div class="eyebrow">03 · App records</div><h2>Search and inspect all 100 apps</h2><p class="muted">Open a row for per-field status, stored evidence and excerpts, automated status, human verdicts, and retrieval notes.</p></div><span class="tag">100 rows</span></div><div class="filters"><input id="q" type="search" placeholder="Search app, API, auth, access, blockers…" aria-label="Search records"><select id="cat"><option value="">All categories</option>{categories}</select><select id="status"><option value="">All research statuses</option>{statuses}</select><select id="build"><option value="">All buildability labels</option>{''.join(f'<option value="{e(x)}">{e(x.replace("_", " "))}</option>' for x in sorted({r.get("buildability","unclear") for r in records}))}</select></div><div class="tablebox"><table><thead><tr><th>Application</th><th>Category</th><th>Research status</th><th>Field status</th><th>Buildability</th><th>API surface / breadth</th><th>Auth</th><th>Access</th><th>MCP</th><th>Blockers</th><th>Evidence links / attempts</th></tr></thead><tbody id="rows">{rows}</tbody></table><div id="empty" class="none">No apps match those filters.</div></div><p class="muted small">External evidence links need internet access when opened. The report itself has no external assets or runtime dependencies.</p></div></section>
<section id="method"><div class="wrap"><div class="head"><div><div class="eyebrow">04 · Method</div><h2>Incremental collection with explicit uncertainty</h2></div></div><div class="workflow"><div class="step"><b>1 · Assignment input</b><p>Load the exact 100 app names/categories and preserve order. Existing 13 v2 records are copied into a separate full-list output without altering their evidence.</p></div><div class="step"><b>2 · Free public fetch</b><p>Try candidate product/developer pages, check robots.txt, extract public HTML body blocks, and follow relevant same-host documentation links. One request at a time with per-host delay and finite timeouts.</p></div><div class="step"><b>3 · Evidence extraction</b><p>Attach URL, title, excerpt, research field, retrieval status, and excerpt-quality label. Unknown fields remain unknown. Every automatically extracted claim remains unverified.</p></div><div class="step"><b>4 · Human review</b><p>Validate the schema, sample claims, open source links, and store human verdicts separately from automated statuses.</p></div></div><div class="grid" style="margin-top:16px"><div class="panel"><h3>Free-pass limitations</h3><ul class="clean"><li>Candidate site URLs were used to avoid scraping search engines after the public search endpoint returned an anti-automation response.</li><li>Many pages expose client-rendered content, refuse automated requests, or did not yield app-matched text; these fields remain unknown.</li><li>Public marketing pages do not establish API availability, plan entitlement, or MCP absence.</li><li>Direct page text extraction is heuristic and not a substitute for careful human comparison.</li><li>Firecrawl API credits were exhausted; no Firecrawl calls or paid APIs were used in this pass.</li></ul></div><div class="panel"><h3>Integration opportunity hypotheses</h3><p>Across sourced records, recurring themes include OAuth onboarding, role/plan-aware access, rate limits, tenant-specific schemas, and bounded MCP tool surfaces. These are product opportunity hypotheses, not quantified market claims.</p><p>Potential integration UX: disclose per-action permissions and plan restrictions before writes, surface rate limits in tool metadata, and make unknown capabilities explicit rather than silently guessing.</p></div></div></div></section>
<section id="verification"><div class="wrap"><div class="head"><div><div class="eyebrow">05 · Manual verification</div><h2>{human_supported} of {len(reviewed)} sampled claims supported</h2><p class="muted">The reviewer reports opening the evidence links and checking each excerpt against the claim.</p></div><a href="manual_verification_summary.md">Review summary ↗</a></div><div class="vgrid"><div class="vcard"><b>{len(reviewed)}</b><span>claims manually reviewed</span></div><div class="vcard"><b>{human_supported}</b><span>supported</span></div><div class="vcard"><b>{metrics['human_verdicts'].get('partially_supported',0)}</b><span>partially supported</span></div><div class="vcard"><b>{metrics['human_verdicts'].get('unsupported',0)+metrics['human_verdicts'].get('source_unavailable',0)+metrics['human_verdicts'].get('unclear',0)}</b><span>unsupported, unavailable, or unclear</span></div></div><div class="callout"><b>Small sample, not overall accuracy.</b> The reviewed apps are {e(human_apps)}. The manual sample is 15 claims out of 100 apps and does not establish accuracy for all research records. Pipeline <code>claim_supported</code> values are displayed separately and were not changed by this report.</div></div></section>
<section id="limits"><div class="wrap"><div class="head"><div><div class="eyebrow">06 · Status</div><h2>The assignment is not complete yet</h2></div></div><div class="grid"><div class="panel"><h3>Current deliverable state</h3><ul class="clean"><li>All {total} app names have a structured record row.</li><li>{usable_apps} apps have at least one readable excerpt.</li><li>{partial} are partial; {blocked} were blocked; {not_researched} have no usable claim excerpt.</li><li>Unknown and unresolved field values remain visible.</li><li>Fifteen claims have manual supported verdicts across three apps.</li></ul></div><div class="panel"><h3>Not established</h3><ul class="clean"><li>Complete research of all required fields for all 100 apps.</li><li>Overall accuracy or human validation of the 87 newly attempted records.</li><li>That a readable excerpt directly supports its attached claim.</li><li>Current status of pages after the recorded fetch date.</li></ul></div></div></div></section></main>
<footer class="footer"><div class="wrap">AppScout · local, self-contained case study · Snapshot {e(latest)} · <a href="{e(apps[0].get('source_url',''))}">Assignment source</a></div></footer>
<script>const q=document.getElementById('q'),cat=document.getElementById('cat'),st=document.getElementById('status'),bu=document.getElementById('build'),body=document.getElementById('rows'),empty=document.getElementById('empty');function filter(){{let n=0;for(const r of body.querySelectorAll('tr')){{const ok=r.dataset.search.toLowerCase().includes(q.value.trim().toLowerCase())&&(!cat.value||r.dataset.category===cat.value)&&(!st.value||r.dataset.status===st.value)&&(!bu.value||r.dataset.build===bu.value);r.hidden=!ok;if(ok)n++}}empty.style.display=n?'none':'block'}}[q,cat,st,bu].forEach(x=>x.addEventListener(x===q?'input':'change',filter));</script></body></html>'''


def main() -> int:
    out = ROOT / "output"
    apps = list(csv.DictReader((ROOT / "data" / "apps.csv").open("r", encoding="utf-8-sig", newline="")))
    raw = json.loads((out / "research_results_free.json").read_text(encoding="utf-8"))
    if len(raw) != len(apps):
        raise ValueError(f"Expected a record for each of {len(apps)} apps, found {len(raw)}")
    records = [AppResearchRecord.model_validate(item) for item in raw]
    names = [r.app_name.casefold() for r in records]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate app records")
    if [r.app_name.casefold() for r in records] != [r["app_name"].casefold() for r in apps]:
        raise ValueError("Full research output must preserve assignment order and names")
    worksheet = list(csv.DictReader((out / "manual_verification_sample.csv").open("r", encoding="utf-8-sig", newline="")))
    by_app = {r.app_name.casefold(): r for r in records}
    reviewed = []
    # Attach worksheet field labels in memory only for the exact reviewed matches.
    for row in worksheet:
        record = by_app[row["app_name"].casefold()]
        ev = next((x for x in record.evidence if x.claim == row["claim"] and str(x.url) == row["evidence_url"]), None)
        if ev is None or row.get("human_verdict") != "supported":
            raise ValueError("Verification worksheet no longer matches its reviewed evidence record")
        reviewed.append(row)
    for record, item in zip(records, raw):
        for row in reviewed:
            if row["app_name"].casefold() == record.app_name.casefold():
                for ev in item.get("evidence", []):
                    if ev.get("claim") == row["claim"] and ev.get("url") == row["evidence_url"]:
                        ev["field"] = row["field"]
    metrics = analyze(raw, apps)
    attempts = Counter(a.get("status", "unknown") for r in raw for a in r.get("source_attempts", []))
    metrics["source_attempt_status"] = attempts
    page = make_html(raw, apps, metrics, reviewed)
    (out / "index.html").write_text(page, encoding="utf-8")
    json_metrics = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in metrics.items()}
    (out / "analysis.json").write_text(json.dumps(json_metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Validated and rendered {len(records)} app records.")
    print(f"Apps with at least one usable excerpt: {metrics['apps_with_usable_evidence']}/{len(apps)}.")
    print(f"Manual sample: {len(reviewed)} claims, {sum(x['human_verdict']=='supported' for x in reviewed)} supported; not an accuracy metric.")
    print(f"Wrote {out / 'index.html'} and {out / 'analysis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
