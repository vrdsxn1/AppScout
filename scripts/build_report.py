"""Build AppScout's self-contained final report from the merged local dataset."""

import csv
import html
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from appscout.analytics import access_flags, analyze, api_bucket, auth_families, research_status
from appscout.evidence_quality import classify_excerpt
from appscout.models import AppResearchRecord

OUT = ROOT / "output"
MERGED = OUT / "research_results_merged.json"
STYLE = r"""
:root{--ink:#172b3a;--muted:#586d78;--paper:#f6f4ee;--card:#fffefa;--line:#dce3df;--green:#126b55;--mint:#daf1e5;--blue:#315f7a;--gold:#e5aa4f;--red:#9d443b;--shadow:0 14px 36px rgba(24,51,62,.07)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.58 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:#075f58;text-decoration-thickness:1px;text-underline-offset:3px;overflow-wrap:anywhere}a:hover{color:#8e4d16}button,input,select{font:inherit}.wrap{width:min(1440px,100%);margin:auto;padding:0 26px}.top{position:sticky;top:0;z-index:10;background:#fbfaf6;border-bottom:1px solid var(--line)}.topbar{height:62px;display:flex;align-items:center;justify-content:space-between;gap:22px}.logo{font-weight:900;font-size:18px;letter-spacing:-.05em;white-space:nowrap}.logo i{color:var(--green);font-style:normal}.nav{display:flex;gap:18px;flex-wrap:wrap;font-size:12px}.nav a{color:var(--muted);text-decoration:none}.tag,.badge{display:inline-flex;align-items:center;border-radius:99px;padding:4px 9px;font-size:10px;font-weight:800;letter-spacing:.025em;background:#edf0ee;color:#40545d}.tag{background:var(--mint);color:var(--green);white-space:nowrap}.hero{padding:56px 0 28px;background:radial-gradient(ellipse at 83% 12%,#e2f0e8,transparent 42%),linear-gradient(180deg,#fbfaf6,var(--paper))}.eyebrow{text-transform:uppercase;color:var(--green);letter-spacing:.14em;font-size:10px;font-weight:850}h1{font-size:clamp(42px,6.2vw,76px);line-height:.98;letter-spacing:-.065em;max-width:1000px;margin:14px 0 18px}h2{font-size:clamp(25px,3vw,34px);letter-spacing:-.045em;line-height:1.1;margin:3px 0 8px}h3{font-size:18px;line-height:1.25;margin:0 0 10px}h4{margin:14px 0 5px}p{margin:7px 0 12px}.lede{font-size:18px;max-width:900px;color:#405964}.notice,.callout{max-width:1060px;padding:15px 18px;background:#fff8e9;border:1px solid #e9cc92;border-left:5px solid var(--gold);border-radius:10px;margin-top:19px}.callout{background:#eef6f1;border-color:#d5e9de;border-left-color:var(--green)}.notice b,.callout b{display:block}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:20px 0 38px}.metric,.panel,.step,.review-card{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}.metric{padding:17px}.metric strong{display:block;font-size:clamp(25px,3vw,36px);letter-spacing:-.05em;line-height:1.15;color:var(--green)}.metric span{font-size:12px;color:var(--muted)}section{padding:37px 0;border-top:1px solid var(--line);scroll-margin-top:76px}.head{display:flex;justify-content:space-between;align-items:end;gap:22px;margin-bottom:19px}.muted{color:var(--muted)}.small{font-size:12px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.panel{padding:20px;min-width:0}.barlist{display:grid;gap:11px}.bar-label{display:flex;justify-content:space-between;gap:12px;font-size:12px;margin-bottom:4px}.bar-label span{color:var(--muted);text-align:right}.track{height:8px;background:#e9efeb;border-radius:99px;overflow:hidden}.track i{display:block;height:100%;background:linear-gradient(90deg,var(--green),#58a78c);border-radius:inherit}.bar-row{margin:8px 0}.state-grid{width:100%;border-collapse:collapse;font-size:12px}.state-grid th,.state-grid td{padding:8px 6px;border-bottom:1px solid var(--line);text-align:right}.state-grid th:first-child,.state-grid td:first-child{text-align:left}.state-grid th{color:var(--muted);font-weight:750}.field-summary{padding:9px 0;border-bottom:1px solid var(--line);font-size:12px}.field-summary div{color:var(--muted)}.chiprow,.pills{display:flex;gap:6px;flex-wrap:wrap}.status,.badge{white-space:nowrap}.s-researched,.q-usable,.h-supported{background:#d9f0e2;color:#176044}.s-partial,.q-navigation,.q-page_shell,.q-insufficient,.h-partially_supported{background:#fff0d5;color:#784b06}.s-blocked,.s-not_researched,.h-unsupported,.h-source_unavailable{background:#f7dfdc;color:#8e3d35}.h-unclear,.a-partially_supported,.a-unsupported,.a-unverified{background:#e9e9e6;color:#45545a}.a-supported{background:#d9eafa;color:#245c83}.filters{display:flex;gap:9px;flex-wrap:wrap;margin:16px 0}.filters input{flex:1;min-width:230px}.filters input,.filters select{padding:10px 12px;border:1px solid #c5d2cc;background:white;border-radius:8px;color:var(--ink)}.table-scroll{display:block;width:100%;max-width:100%;overflow:auto;overscroll-behavior-x:contain;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:13px;background:var(--card);box-shadow:var(--shadow)}table.directory{border-collapse:collapse;table-layout:fixed;width:1320px;min-width:1320px;font-size:12px}table.directory th{position:sticky;top:0;background:#edf3ef;color:#40545d;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.065em;z-index:1}table.directory td,table.directory th{padding:11px;border-bottom:1px solid #e7ece9;vertical-align:top;white-space:normal;overflow-wrap:anywhere}table.directory td:nth-child(1),table.directory th:nth-child(1){width:280px}table.directory td:nth-child(2),table.directory th:nth-child(2){width:160px}table.directory td:nth-child(3),table.directory th:nth-child(3){width:125px}table.directory td:nth-child(4),table.directory th:nth-child(4){width:145px}table.directory td:nth-child(5),table.directory th:nth-child(5){width:240px}table.directory td:nth-child(6),table.directory th:nth-child(6){width:95px}table.directory td:nth-child(7),table.directory th:nth-child(7){width:190px}td small{display:block;color:var(--muted);font-size:11px;margin-top:5px;overflow-wrap:anywhere}.status,.verdict{display:inline-flex;border-radius:99px;padding:4px 8px;font-size:10px;font-weight:800;background:#edf0ee;color:#526269}.v-build_now{background:#d9f0e2;color:#176044}.v-build_with_restrictions{background:#fff0d5;color:#784b06}.v-needs_outreach{background:#f7dfdc;color:#8e3d35}.v-unclear{background:#e9e9e6;color:#45545a}details summary{cursor:pointer;color:#075f58;font-weight:750}details summary:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #2e7f73;outline-offset:2px}.app-details{margin-top:7px}.app-details summary{font-size:11px}.detail-body{padding:12px 0 5px}.detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.detail-field{border:1px solid var(--line);border-radius:8px;padding:10px;overflow-wrap:anywhere}.detail-field b{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:4px}.detail-field p{margin:0;font-size:12px}.evidence-list{list-style:none;margin:10px 0;padding:0}.evidence-item{padding:13px 0;border-top:1px solid var(--line);overflow-wrap:anywhere}.evidence-item blockquote{margin:8px 0;padding:10px 12px;background:#f1f6f2;border-left:3px solid #93c5af;color:#405963;font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}.evidence-claim{font-size:12px}.evidence-notes{background:#eef3fb;border-left:3px solid #6e99b8;padding:8px 10px;font-size:12px}.attempt-list{padding-left:20px;font-size:12px}.attempt-list li{margin:5px 0;overflow-wrap:anywhere}.mini-list{padding-left:18px;margin:5px 0;font-size:12px}.empty{display:none;text-align:center;padding:18px;color:var(--muted)}.review-table{width:100%;border-collapse:collapse;font-size:12px}.review-table th,.review-table td{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}.review-table th{background:#edf3ef;font-size:10px;text-transform:uppercase;letter-spacing:.05em}.review-table td:nth-child(1){white-space:nowrap}.review-table td:nth-child(3){min-width:240px}.review-table td:nth-child(4){min-width:230px}.scroll-table{overflow:auto;max-width:100%;border:1px solid var(--line);border-radius:10px}.review-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px}.review-card{padding:15px}.review-card b{font-size:27px;display:block}.review-card span{font-size:12px;color:var(--muted)}.workflow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px}.step{padding:16px}.step b{display:block;color:var(--green);margin-bottom:6px}.step p{font-size:12px;color:var(--muted);margin:0}.clean{padding-left:19px}.clean li{margin:6px 0}.audit{max-height:650px;overflow:auto;background:#f3f5f3;padding:14px;border:1px solid var(--line);border-radius:9px;white-space:pre-wrap;overflow-wrap:anywhere;font:11px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}.footer{padding:34px 0 48px;color:var(--muted);font-size:12px}.counter{font-size:12px;color:var(--muted);align-self:center}.source-type{font-size:10px;color:var(--muted)}.no-wrap{white-space:nowrap}.section-intro{max-width:900px;color:var(--muted)}.pill-warning{background:#fff0d5;color:#784b06}.pill-info{background:#d9eafa;color:#245c83}
.s-researched,.q-usable,.h-supported,.v-build_now{background:#d9f0e2;color:#176044}.s-partial,.q-navigation,.q-page_shell,.q-insufficient,.h-partially_supported,.v-build_with_restrictions{background:#fff0d5;color:#784b06}.s-blocked,.s-not-researched,.h-unsupported,.h-source_unavailable,.v-needs_outreach{background:#f7dfdc;color:#8e3d35}.h-unclear,.a-partially_supported,.a-unsupported,.a-unverified,.v-unclear{background:#e9e9e6;color:#45545a}.a-supported{background:#d9eafa;color:#245c83}
@media(max-width:900px){.wrap{padding:0 16px}.nav{display:none}.grid{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.workflow{grid-template-columns:repeat(2,minmax(0,1fr))}.review-cards{grid-template-columns:repeat(3,minmax(0,1fr))}.head{align-items:start;display:block}}
@media(max-width:540px){.hero{padding-top:38px}.metrics{gap:8px}.metric{padding:12px}.metric strong{font-size:25px}.review-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.workflow{grid-template-columns:1fr 1fr}.detail-grid{grid-template-columns:1fr}.tag{font-size:9px}.topbar{height:56px}}
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def show_value(value) -> str:
    if isinstance(value, list):
        return " · ".join(str(item) for item in value) if value else "Unknown / no value recorded"
    return str(value) if value not in (None, "") else "Unknown / no value recorded"


def url_ok(value: str) -> bool:
    return urlsplit(str(value)).scheme in {"http", "https"} and bool(urlsplit(str(value)).netloc)


def exact_evidence(record: dict, row: dict) -> list[dict]:
    return [
        evidence for evidence in record.get("evidence", [])
        if evidence.get("field") == row.get("field")
        and evidence.get("claim") == row.get("claim")
        and str(evidence.get("url")) == row.get("evidence_url")
        and (evidence.get("excerpt") or "") == (row.get("retrieved_excerpt") or row.get("excerpt") or "")
    ]


def status_class(status: str) -> str:
    return "s-" + status.replace("_", "-")


def badge(label: str, value: str, css: str = "") -> str:
    return f'<span class="badge {esc(css)}">{esc(label)}: {esc(value.replace("_", " "))}</span>'


def bars_html(counter: Counter, denominator: int | None = None) -> str:
    if not counter:
        return '<p class="muted">No records for this measure.</p>'
    maximum = max(counter.values()) or 1
    rows = []
    for label, value in counter.most_common():
        width = max(2, round(value / maximum * 100))
        amount = f"{value}/{denominator}" if denominator else str(value)
        rows.append(f'<div class="bar-row"><div class="bar-label"><b>{esc(label)}</b><span>{amount}</span></div><div class="track"><i style="width:{width}%"></i></div></div>')
    return "".join(rows)


def status_counters(records: list[dict]) -> Counter:
    return Counter(research_status(record) for record in records)


def evidence_recheck(records: list[dict]) -> tuple[Counter, int, int, int]:
    current = Counter()
    usable_apps = 0
    unique_urls = set()
    retrieved = 0
    for record in records:
        app_has_usable = False
        for ev in record.get("evidence", []):
            excerpt = ev.get("excerpt")
            quality = classify_excerpt(excerpt)[0]
            current[quality] += 1
            if ev.get("retrieval_status") == "retrieved":
                retrieved += 1
                if quality == "usable" and excerpt:
                    app_has_usable = True
            if url_ok(ev.get("url", "")):
                unique_urls.add(str(ev["url"]))
        usable_apps += app_has_usable
    return current, usable_apps, len(unique_urls), retrieved


def merge_stats(records: list[dict]) -> dict:
    original = json.loads((OUT / "research_results_free.json").read_text(encoding="utf-8"))
    scrapedo = json.loads((OUT / "research_results_scrapedo.json").read_text(encoding="utf-8"))
    key = lambda ev: (ev.get("field"), ev.get("claim"), str(ev.get("url")), ev.get("excerpt") or "")
    original_keys = {(r["app_name"], key(ev)) for r in original for ev in r.get("evidence", [])}
    scrape_keys = {(r["app_name"], key(ev)) for r in scrapedo for ev in r.get("evidence", [])}
    progress = {"research_status", "research_note", "source_attempts", "source_queue", "evidence"}
    differing_fields: dict[str, list[str]] = {}
    for old, new in zip(original, scrapedo):
        fields = [f for f in set(old) | set(new) if f not in progress and old.get(f) != new.get(f)]
        if fields:
            differing_fields[old["app_name"]] = sorted(fields)
    return {
        "original_evidence": sum(len(r.get("evidence", [])) for r in original),
        "scrapedo_evidence": sum(len(r.get("evidence", [])) for r in scrapedo),
        "added": len(scrape_keys - original_keys),
        "deduplicated": len(scrape_keys & original_keys),
        "conflict_apps": len(differing_fields),
        "conflict_fields": differing_fields,
        "attempts": sum(len(r.get("source_attempts", [])) for r in records),
        "attempt_status": Counter(a.get("status", "unknown") for r in records for a in r.get("source_attempts", [])),
    }


def review_summary(rows: list[dict]) -> Counter:
    return Counter(row.get("human_verdict", "").strip() for row in rows)


def evidence_item(ev: dict) -> str:
    url = str(ev.get("url", ""))
    link = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(ev.get("source_title") or url or "Source")}</a>' if url_ok(url) else esc(ev.get("source_title") or "Source URL unavailable")
    excerpt = ev.get("excerpt") or ev.get("retrieval_note") or "No excerpt stored."
    stored_quality = ev.get("evidence_quality") or "insufficient"
    current_quality, reason = classify_excerpt(ev.get("excerpt"))
    human = ev.get("human_verdict") or "not reviewed"
    notes = ev.get("reviewer_notes")
    notes_html = f'<p class="evidence-notes"><b>Reviewer note:</b> {esc(notes)}</p>' if notes else ""
    return (
        '<li class="evidence-item">'
        f'<div>{link} <span class="source-type">· {esc(ev.get("source_type") or "source type unknown")}</span></div>'
        f'<p class="evidence-claim"><b>{esc(ev.get("field") or "Field not mapped")}</b> — {esc(ev.get("claim") or "No claim text stored.")}</p>'
        f'<blockquote>{esc(excerpt)}</blockquote><div class="pills">'
        f'{badge("Retrieval", ev.get("retrieval_status", "not_attempted"), "pill-info")}'
        f'{badge("Stored quality", stored_quality, "q-" + stored_quality)}'
        f'{badge("Current text check", current_quality, "q-" + current_quality)}'
        f'{badge("Automated claim", ev.get("claim_supported", "unverified"), "a-" + (ev.get("claim_supported") or "unverified"))}'
        f'{badge("Human review", human, "h-" + human.replace(" ", "_"))}</div>'
        f'<small>{esc(reason)} Stored quality is preserved as recorded; current text check is a report-time readability recheck only.</small>{notes_html}</li>'
    )


def app_details(record: dict) -> str:
    fields = [
        ("Description", record.get("description")),
        ("Authentication", record.get("auth_methods")),
        ("Access model", record.get("access_model")),
        ("API type", record.get("api_type")),
        ("API breadth", record.get("api_breadth")),
        ("MCP status", record.get("mcp_status")),
        ("Buildability", record.get("buildability")),
        ("Blockers", record.get("blockers")),
        ("Research note", record.get("research_note")),
    ]
    field_html = "".join(f'<div class="detail-field"><b>{esc(label)}</b><p>{esc(show_value(value))}</p></div>' for label, value in fields)
    evidence = "".join(evidence_item(ev) for ev in record.get("evidence", [])) or '<li class="muted">No claim-level evidence recorded.</li>'
    attempts = []
    for item in record.get("source_attempts", []):
        url = str(item.get("url", ""))
        link = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(url)}</a>' if url_ok(url) else esc(url or "URL unavailable")
        attempts.append(f'<li>{link} — <b>{esc(item.get("status", "unknown"))}</b>{": " + esc(item["note"]) if item.get("note") else ""}</li>')
    attempt_html = "".join(attempts) or '<li class="muted">No source-attempt log recorded.</li>'
    return (
        '<details class="app-details"><summary>Inspect fields, claims, sources, and review</summary><div class="detail-body">'
        f'<div class="detail-grid">{field_html}</div><h4>Evidence and provenance ({len(record.get("evidence", []))} records)</h4>'
        f'<ul class="evidence-list">{evidence}</ul><h4>Source attempts ({len(record.get("source_attempts", []))})</h4>'
        f'<ul class="attempt-list">{attempt_html}</ul></div></details>'
    )


def app_row(record: dict) -> str:
    app = record["app_name"]
    status = research_status(record)
    human = [ev.get("human_verdict") for ev in record.get("evidence", []) if ev.get("human_verdict")]
    human_text = Counter(human)
    review_html = "<br>".join(f'{count} {esc(verdict.replace("_", " "))}' for verdict, count in human_text.items()) if human_text else "Not sampled"
    blockers = record.get("blockers", [])
    blocker_text = " · ".join(str(item) for item in blockers[:2]) if blockers else "None recorded"
    search_content = [app, record.get("category", ""), record.get("description", ""), record.get("api_type", ""), record.get("api_breadth", ""), record.get("access_model", ""), record.get("mcp_status", ""), *record.get("auth_methods", []), *blockers]
    for ev in record.get("evidence", []):
        search_content.extend([ev.get("claim", ""), ev.get("source_title", ""), ev.get("excerpt", "")])
    search_data = " ".join(str(item) for item in search_content)
    build = record.get("buildability", "unclear")
    summary = (
        f'<strong>{esc(app)}</strong><small>{esc(record.get("description") or "Description unknown")}</small>'
        f'{app_details(record)}'
    )
    return (
        f'<tr data-category="{esc(record.get("category", ""))}" data-status="{esc(status)}" data-build="{esc(build)}" data-human="{"reviewed" if human else "none"}" data-search="{esc(search_data)}">'
        f'<td>{summary}</td><td>{esc(record.get("category", ""))}</td>'
        f'<td><span class="status {status_class(status)}">{esc(status.replace("_", " "))}</span></td>'
        f'<td><span class="verdict v-{esc(build)}">{esc(build.replace("_", " "))}</span></td>'
        f'<td>{esc(blocker_text)}</td><td>{len(record.get("evidence", []))}</td><td>{review_html}</td></tr>'
    )


def human_sample_rows(rows: list[dict], by_name: dict[str, dict]) -> str:
    out = []
    for row in rows:
        record = by_name[row["app_name"].casefold()]
        matches = exact_evidence(record, row)
        if len(matches) != 1:
            raise ValueError(f"Human worksheet evidence does not match exactly: {row['app_name']} / {row['field']}")
        ev = matches[0]
        verdict = row["human_verdict"]
        out.append(
            f'<tr><td>{esc(row["app_name"])}</td><td>{esc(row["category"])}</td><td>{esc(row["field"])}</td>'
            f'<td><span class="badge h-{esc(verdict)}">{esc(verdict.replace("_", " "))}</span></td>'
            f'<td>{esc(row["claim"])}</td><td><a href="{esc(row["evidence_url"])}" target="_blank" rel="noopener noreferrer">{esc(ev.get("source_title") or row["evidence_url"])}</a>'
            f'<details><summary>Excerpt</summary><blockquote>{esc(ev.get("excerpt") or "No excerpt stored")}</blockquote></details></td>'
            f'<td>{esc(row.get("reviewer_notes") or "—")}</td></tr>'
        )
    return "".join(out)


def legacy_rows(rows: list[dict]) -> str:
    result = []
    for row in rows:
        result.append(
            f'<tr><td>{esc(row["app_name"])}</td><td>{esc(row["field"])}</td><td>{esc(row["claim"])}</td>'
            f'<td><a href="{esc(row["evidence_url"])}" target="_blank" rel="noopener noreferrer">Source</a></td>'
            f'<td><span class="badge h-supported">supported</span></td></tr>'
        )
    return "".join(result)


def make_html(records: list[dict], apps: list[dict], metrics: dict, review_rows: list[dict], legacy_review: list[dict], merge: dict, merge_audit: str, error_analysis: str) -> str:
    status_counts = status_counters(records)
    stored_quality = Counter(ev.get("evidence_quality") or "insufficient" for r in records for ev in r.get("evidence", []))
    current_quality, usable_apps, unique_urls, retrieved_count = evidence_recheck(records)
    evidence_count = sum(len(r.get("evidence", [])) for r in records)
    human_counts = review_summary(review_rows)
    legacy_counts = review_summary(legacy_review)
    source_types = Counter(ev.get("source_type") or "unspecified" for r in records for ev in r.get("evidence", []))
    category_status: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        category_status[record["category"]][research_status(record)] += 1
    category_rows = []
    for category in sorted(category_status):
        counts = category_status[category]
        category_rows.append(
            f'<tr><td>{esc(category)}</td><td>{counts["researched"]}</td><td>{counts["partial"]}</td><td>{counts["blocked"]}</td><td>{counts["not_researched"]}</td><td>{sum(counts.values())}</td></tr>'
        )

    app_rows = "".join(app_row(record) for record in records)
    category_options = "".join(f'<option value="{esc(category)}">{esc(category)}</option>' for category in sorted({r["category"] for r in records}))
    build_options = "".join(f'<option value="{esc(build)}">{esc(build.replace("_", " "))}</option>' for build in sorted({r.get("buildability", "unclear") for r in records}))
    review_rows_html = human_sample_rows(review_rows, {r["app_name"].casefold(): r for r in records})
    legacy_rows_html = legacy_rows(legacy_review)
    category_status_html = "".join(category_rows)
    unknown_html = "".join(f'<li><b>{count}</b> apps explicitly mark <code>{esc(field)}</code> unknown or unclear.</li>' for field, count in metrics["unknown_fields"].most_common()) or "<li>No explicit unknown marker found.</li>"
    field_status_html = "".join(
        f'<div class="field-summary"><b>{esc(field)}</b><div>{" · ".join(f"{esc(state)}: {count}" for state, count in counter.most_common())}</div></div>'
        for field, counter in metrics["field_status"].items()
    )
    source_status_html = bars_html(merge["attempt_status"])
    unique_app_reviewed = len({r["app_name"] for r in review_rows})
    flagged_failed = 0
    for row in review_rows:
        if row["human_verdict"] in {"unsupported", "unclear"}:
            ev = exact_evidence(next(r for r in records if r["app_name"].casefold() == row["app_name"].casefold()), row)[0]
            if classify_excerpt(ev.get("excerpt"))[0] != "usable":
                flagged_failed += 1
    source_count = len(source_types)
    latest = max((str(r.get("last_checked") or "") for r in records), default="not recorded")
    all_human_supported = sum(1 for r in records for ev in r.get("evidence", []) if ev.get("human_verdict") == "supported")
    current_categories = Counter(research_status(r) for r in records)
    merge_conflict_apps = merge["conflict_apps"]
    conflict_fields_html = ", ".join(f"{esc(field)} ({count})" for field, count in Counter(field for fields in merge["conflict_fields"].values() for field in fields).most_common()) or "none"
    audit_html = esc(merge_audit)
    error_html = esc(error_analysis)
    assignment_source = next((r.get("source_url") for r in apps if r.get("source_url")), "")

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Source-linked research on integration readiness for AI agents across 100 software apps."><title>AppScout — 100-app integration readiness research</title><style>{STYLE}</style></head>
<body><header class="top"><div class="wrap topbar"><a class="logo" href="#top" aria-label="AppScout home">APP<i>SCOUT</i></a><nav class="nav" aria-label="Report sections"><a href="#coverage">Coverage</a><a href="#findings">Findings</a><a href="#directory">App directory</a><a href="#verification">Human review</a><a href="#method">Method</a><a href="#provenance">Provenance</a></nav><span class="tag">100-APP RESEARCH SNAPSHOT</span></div></header>
<main id="top"><section class="hero" style="border:0"><div class="wrap"><div class="eyebrow">Product operations · AI agent integrations</div><h1>Can an AI agent actually get in?</h1><p class="lede">AppScout maps API access, authentication, plan and permission gates, API scope, MCP availability, and implementation blockers for the exact 100-app assignment list.</p><div class="notice"><b>100 apps are represented; research depth varies.</b> The merged dataset has {status_counts['researched']} researched records, {status_counts['partial']} partial, {status_counts['blocked']} blocked, and {status_counts['not_researched']} not researched. A record or readable excerpt is not proof that every claim is correct.</div>
<div class="metrics"><div class="metric"><strong>{len(records)} / {len(apps)}</strong><span>assignment apps represented in original order</span></div><div class="metric"><strong>{usable_apps} / {len(records)}</strong><span>apps with a retrieved excerpt classified readable by the current local check</span></div><div class="metric"><strong>{evidence_count}</strong><span>evidence records with claim and source metadata</span></div><div class="metric"><strong>{unique_urls}</strong><span>unique evidence source URLs</span></div></div></div></section>

<section id="coverage"><div class="wrap"><div class="head"><div><div class="eyebrow">01 · Coverage</div><h2>Coverage, with status kept explicit</h2><p class="section-intro">Status counts are mutually exclusive per app. “Researched” includes legacy records whose status field is null but which contain evidence; “partial” is reported separately. “Readable evidence” is an excerpt-level classifier result, not claim verification.</p></div>{f'<a href="{esc(assignment_source)}" target="_blank" rel="noopener noreferrer">Assignment source ↗</a>' if url_ok(assignment_source) else ''}</div>
<div class="grid"><article class="panel"><h3>App research status</h3><div class="chiprow"><span class="badge s-researched">Researched {status_counts['researched']}</span><span class="badge s-partial">Partial {status_counts['partial']}</span><span class="badge s-blocked">Blocked {status_counts['blocked']}</span><span class="badge s-not_researched">Not researched {status_counts['not_researched']}</span></div><p class="muted small">The status reflects record-level progress. Blocked and not-researched records are not silently converted to positive or negative capability findings.</p><div class="barlist">{bars_html(status_counts, len(records))}</div></article>
<article class="panel"><h3>Evidence retrieval and readability</h3><p><b>{retrieved_count}</b> evidence records have retrieval status <code>retrieved</code>. <b>{usable_apps}</b> apps have at least one excerpt the current local classifier calls <code>usable</code>. The classifier is re-run on stored excerpt text at report build time; it does not alter stored labels or support status.</p><div class="grid"><div><b class="small">Stored quality labels</b>{bars_html(stored_quality)}</div><div><b class="small">Current text recheck</b>{bars_html(current_quality)}</div></div><p class="muted small">Stored vs current counts can differ because the classifier was improved after collection. Both are readability-only labels.</p></article></div>
<article class="panel" style="margin-top:15px"><h3>Coverage by assignment category</h3><div class="scroll-table"><table class="state-grid"><thead><tr><th>Category</th><th>Researched</th><th>Partial</th><th>Blocked</th><th>Not researched</th><th>Total apps</th></tr></thead><tbody>{category_status_html}</tbody></table></div></article>
<div class="callout"><b>Evidence scope.</b> {evidence_count} evidence records point to {unique_urls} unique source URLs. A URL identifies where the claim should be checked; it does not establish support by itself. Automated status, stored/current excerpt quality, and any human verdict appear separately in each app detail.</div></div></section>

<section id="findings"><div class="wrap"><div class="head"><div><div class="eyebrow">02 · Cross-category findings</div><h2>Patterns in recorded fields</h2><p class="section-intro">These are counts of stored app-level values and transparent keyword groupings. They describe this dataset's coverage, not universal product behavior. Access and blocker groupings overlap.</p></div></div>
<div class="grid"><article class="panel"><h3>Buildability labels</h3>{bars_html(metrics['buildability'], len(records))}<p class="muted small">Research judgments, not tested integration outcomes.</p></article><article class="panel"><h3>Recorded API surfaces</h3>{bars_html(metrics['api_surfaces'], len(records))}<p class="muted small">Unknown/unclear remains a distinct bucket.</p></article><article class="panel"><h3>Authentication families mentioned</h3>{bars_html(metrics['auth_families'])}<p class="muted small">An app can mention multiple auth families. No methods recorded does not prove auth is unavailable.</p></article><article class="panel"><h3>Access wording patterns</h3>{bars_html(metrics['access_characteristics'])}<p class="muted small">Heuristic scan of stored access-model text; “free/trial” and “paid” can coexist.</p></article><article class="panel"><h3>Common blocker wording</h3>{bars_html(metrics['blocker_topics'], len(records))}<p class="muted small">Keyword groupings from stored blockers and access text. They are not independently verified counts of actual restrictions.</p></article><article class="panel"><h3>Source-attempt outcomes</h3>{source_status_html}<p class="muted small">{merge['attempts']} attempt records preserved across both inputs.</p></article></div>
<div class="grid" style="margin-top:15px"><article class="panel"><h3>MCP field coverage</h3><p><b>{sum(not ("unknown" in str(r.get("mcp_status", "")).lower() or "unclear" in str(r.get("mcp_status", "")).lower()) for r in records)}</b> records have a non-unknown MCP field; <b>{sum(("unknown" in str(r.get("mcp_status", "")).lower() or "unclear" in str(r.get("mcp_status", "")).lower()) for r in records)}</b> explicitly say unknown or unclear.</p><p class="muted small">A non-unknown field may still be unverified. Inspect the linked claim and status for each app.</p></article><article class="panel"><h3>API-field coverage</h3><p><b>{sum(api_bucket(r.get("api_type", "")) not in {"Unknown / unclear", "Other / unspecified"} for r in records)}</b> records name a REST or GraphQL surface; <b>{sum(api_bucket(r.get("api_type", "")) == "Unknown / unclear" for r in records)}</b> are explicitly unknown or unclear.</p><p class="muted small">Coverage does not imply breadth, plan eligibility, write access, or stable version support.</p></article></div>
<div class="panel" style="margin-top:15px"><h3>Field status across 100 records</h3>{field_status_html}<div class="callout"><b>Unknown is a valid result.</b> Empty values, blocked sources, missing evidence, unverified claims, and unsupported human verdicts have different meanings. Do not read an empty or blocked field as “no API” or “not supported.”</div></div></div></section>

<section id="directory"><div class="wrap"><div class="head"><div><div class="eyebrow">03 · App directory</div><h2>Search and inspect all 100 apps</h2><p class="section-intro">Each expandable app row includes all recorded fields, every evidence claim and excerpt, source links, source attempts, quality labels, automated status, human verdict, and reviewer note.</p></div><span class="tag">{len(records)} app records</span></div>
<div class="filters"><input id="search" type="search" placeholder="Search apps, claims, sources, API, auth…" aria-label="Search apps and evidence"><select id="category" aria-label="Filter by category"><option value="">All categories</option>{category_options}</select><select id="status" aria-label="Filter by research status"><option value="">All research statuses</option><option value="researched">Researched</option><option value="partial">Partial</option><option value="blocked">Blocked</option><option value="not_researched">Not researched</option></select><select id="buildability" aria-label="Filter by buildability"><option value="">All buildability labels</option>{build_options}</select><select id="human" aria-label="Filter by human review"><option value="">All human review states</option><option value="reviewed">Has human review</option><option value="none">No sampled evidence</option></select><span id="result-count" class="counter" aria-live="polite">Showing {len(records)} apps</span></div>
<div class="table-scroll" role="region" aria-label="Scrollable all-app research directory" tabindex="0"><table class="directory"><thead><tr><th>App and details</th><th>Category</th><th>Research status</th><th>Buildability</th><th>Main blockers</th><th>Evidence</th><th>Human review</th></tr></thead><tbody id="app-rows">{app_rows}</tbody></table></div><div id="no-results" class="empty">No apps match the selected filters.</div><p class="muted small">The report is self-contained and works offline. Opening external source links requires an internet connection.</p></div></section>

<section id="verification"><div class="wrap"><div class="head"><div><div class="eyebrow">04 · Human verification</div><h2>The 20-claim Scrape.do review sample</h2><p class="section-intro">The sample was stratified across categories and evidence types, with emphasis on excerpts then marked usable; several borderline examples were intentionally included. It is small and not statistically representative.</p></div></div>
<div class="review-cards"><article class="review-card"><b>{len(review_rows)}</b><span>claims reviewed</span></article><article class="review-card"><b>{human_counts['supported']}</b><span>supported</span></article><article class="review-card"><b>{human_counts['unsupported']}</b><span>unsupported</span></article><article class="review-card"><b>{human_counts['unclear']}</b><span>unclear</span></article><article class="review-card"><b>{human_counts['partially_supported']}</b><span>partially supported</span></article><article class="review-card"><b>{human_counts['source_unavailable']}</b><span>source unavailable</span></article></div>
<div class="callout"><b>Not an accuracy estimate.</b> This 20-claim stratified sample does not represent all 100 apps or all 356 evidence records. Of the 8 unsupported/unclear sample excerpts, the current text classifier flags {flagged_failed} as navigation, page shell, or insufficient; Plaid remains readable but its human verdict is unclear. Readability and claim support are separate checks.</div>
<div class="panel" style="margin-top:15px"><h3>Reviewed claims and reviewer notes</h3><div class="scroll-table"><table class="review-table" id="scrapedo-review-table"><thead><tr><th>App</th><th>Category</th><th>Field</th><th>Human verdict</th><th>Claim</th><th>Source and excerpt</th><th>Reviewer note</th></tr></thead><tbody>{review_rows_html}</tbody></table></div></div>
<details class="panel" style="margin-top:15px"><summary>Earlier v2 sample: {len(legacy_review)} claims, {legacy_counts['supported']} supported</summary><p class="muted small">This is a separate earlier review of Salesforce, HubSpot, and Pipedrive. It is not combined with the 20-claim Scrape.do sample and is not a general accuracy measure.</p><div class="scroll-table"><table class="review-table" id="legacy-review-table"><thead><tr><th>App</th><th>Field</th><th>Claim</th><th>Evidence</th><th>Human verdict</th></tr></thead><tbody>{legacy_rows_html}</tbody></table></div></details>
<article class="panel" style="margin-top:15px"><h3>Observed evidence extraction failures and fixes</h3><p>Manual review found metadata-heavy pricing/API pages, link-only navigation, a flattened status table, and an ambiguous Plaid MCP excerpt. The current classifier now flags repeated metadata as <code>page_shell</code>, linked index lists without prose as <code>navigation</code>, and flattened status-code tables as <code>insufficient</code>. These are readability filters only; no claim is marked supported by them.</p><details><summary>Read claim-by-claim error analysis</summary><pre class="audit">{error_html}</pre></details></article></div></section>

<section id="method"><div class="wrap"><div class="head"><div><div class="eyebrow">05 · Method and limitations</div><h2>What this snapshot does—and does not—establish</h2><p class="section-intro">This report presents the merged record set as-is, while distinguishing source retrieval, excerpt readability, automated claim status, and human review.</p></div></div>
<div class="workflow"><article class="step"><b>1 · Assignment list</b><p>Read the exact 100 app names/categories and preserve assignment order.</p></article><article class="step"><b>2 · Public-source research</b><p>Use official developer docs, public product pages, and public repositories where available. Respect access restrictions and robots rules.</p></article><article class="step"><b>3 · Capture and validate</b><p>Store claim, field, URL, source title, excerpt, retrieval state, and quality flag. Validate each record with Pydantic.</p></article><article class="step"><b>4 · Human review</b><p>Open a sample of URLs and compare the full page with the specific claim. Save verdicts separately from pipeline status.</p></article></div>
<div class="grid" style="margin-top:15px"><article class="panel"><h3>Evidence quality and verification labels</h3><ul class="clean"><li><b>Retrieval</b> says whether content was fetched or access failed.</li><li><b>Stored quality</b> is the label saved in that dataset record.</li><li><b>Current text check</b> re-runs the local format/readability classifier for this report.</li><li><b>Automated claim status</b> remains <code>unverified</code> unless the pipeline recorded another explicit status.</li><li><b>Human verdict</b> records the sampled reviewer result; notes remain attached to the reviewed evidence.</li></ul><p>The classifier does not judge semantic support. A readable excerpt, successful retrieval, or URL is not proof that a claim is accurate.</p></article><article class="panel"><h3>Access limitations</h3><ul class="clean"><li>Firecrawl credits were exhausted; this final merge/report did not call Firecrawl.</li><li>Scrape.do was used for public pages with normal fetches unless rendering was explicitly needed. Requests were bounded and results saved incrementally.</li><li>The Stripe API documentation URL was explicitly disallowed by Scrape.do (HTTP 400); it was not retried. No alternate Stripe claim is inferred here.</li><li>Blocked, rate-limited, unavailable, and unresearched states are retained in records and attempt logs.</li><li>External source URLs are not live-tested during this report build; link validation is structural and local.</li></ul></article></div>
<div class="callout"><b>Remaining limitations.</b> Research depth is partial for many apps. Source pages can change, excerpts can omit qualifications, and evidence-to-field mapping can be weak even when text is readable. Buildability is a research judgment, not a working integration test. No overall accuracy claim is made.</div></div></section>

<section id="provenance"><div class="wrap"><div class="head"><div><div class="eyebrow">06 · Evidence and provenance</div><h2>How the merged dataset was assembled</h2></div></div><div class="grid"><article class="panel"><h3>Merge summary</h3><ul class="clean"><li>Authoritative report source: <code>output/research_results_merged.json</code>.</li><li>Original evidence records retained: {merge['original_evidence']}.</li><li>Scrape.do records considered: {merge['scrapedo_evidence']}; exact duplicates: {merge['deduplicated']}; additions: {merge['added']}.</li><li>Deduplication required app, field, full claim, exact URL, and excerpt to match. Different claims/excerpts at the same URL remain distinct.</li><li>{merge_conflict_apps} apps had differing assessment fields across inputs; original values were retained. Differing fields include {conflict_fields_html}.</li><li>All 13 v2 records and 15 original supported entries remain unchanged.</li><li>{len(review_rows)} Scrape.do human verdicts and their reviewer notes remain attached to exact evidence records.</li></ul></article><article class="panel"><h3>Evidence index</h3><p>{evidence_count} claim-level records, {unique_urls} distinct source URLs, {source_count} source-type labels, and {merge['attempts']} source-attempt records are available in the directory. Each evidence item displays its source link, claim, excerpt, retrieval result, two readability labels, automated status, human verdict, and reviewer note when recorded.</p><p class="muted small">Claims with missing source text remain visible as missing/insufficient. Human unsupported and unclear results are not collapsed into automated status.</p></article></div>
<details class="panel" style="margin-top:15px"><summary>Expand the complete merge audit, including per-app field conflicts</summary><pre class="audit">{audit_html}</pre></details></div></section></main>
<footer class="footer"><div class="wrap">AppScout · self-contained local report · Dataset snapshot date {esc(latest)} · {len(records)} apps · No external assets required.</div></footer>
<script>
(() => {{
  const search = document.getElementById('search');
  const category = document.getElementById('category');
  const status = document.getElementById('status');
  const buildability = document.getElementById('buildability');
  const human = document.getElementById('human');
  const rows = Array.from(document.querySelectorAll('#app-rows tr'));
  const empty = document.getElementById('no-results');
  const count = document.getElementById('result-count');
  function filterRows() {{
    const needle = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    for (const row of rows) {{
      const match = row.dataset.search.toLocaleLowerCase().includes(needle)
        && (!category.value || row.dataset.category === category.value)
        && (!status.value || row.dataset.status === status.value)
        && (!buildability.value || row.dataset.build === buildability.value)
        && (!human.value || row.dataset.human === human.value);
      row.hidden = !match;
      if (match) visible += 1;
    }}
    count.textContent = `Showing ${{visible}} of ${{rows.length}} apps`;
    empty.style.display = visible ? 'none' : 'block';
  }}
  search.addEventListener('input', filterRows);
  [category, status, buildability, human].forEach((select) => select.addEventListener('change', filterRows));
}})();
</script></body></html>'''


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def check_reviews(records: list[dict], new_rows: list[dict], legacy_rows: list[dict]) -> None:
    by_name = {record["app_name"].casefold(): record for record in records}
    if len(new_rows) != 20:
        raise ValueError(f"Expected 20 Scrape.do reviewed rows, got {len(new_rows)}")
    if len(legacy_rows) != 15:
        raise ValueError(f"Expected 15 original reviewed rows, got {len(legacy_rows)}")
    for row in new_rows:
        record = by_name.get(row["app_name"].casefold())
        matches = exact_evidence(record, row) if record else []
        if len(matches) != 1 or matches[0].get("human_verdict") != row.get("human_verdict") or matches[0].get("reviewer_notes", "") != row.get("reviewer_notes", ""):
            raise ValueError(f"Scrape.do review not preserved exactly: {row['app_name']} / {row['field']}")
    for row in legacy_rows:
        record = by_name.get(row["app_name"].casefold())
        matches = [ev for ev in record.get("evidence", []) if ev.get("claim") == row["claim"] and str(ev.get("url")) == row["evidence_url"]] if record else []
        if len(matches) != 1 or row.get("human_verdict") != "supported" or matches[0].get("human_verdict") != "supported":
            raise ValueError(f"Original v2 review not preserved: {row['app_name']} / {row['field']}")


def main() -> int:
    apps = read_csv(ROOT / "data" / "apps.csv")
    raw = json.loads(MERGED.read_text(encoding="utf-8"))
    if len(raw) != len(apps):
        raise ValueError(f"Expected {len(apps)} app records, got {len(raw)}")
    records = [AppResearchRecord.model_validate(item) for item in raw]
    if [(r.app_name.casefold(), r.category) for r in records] != [(r["app_name"].casefold(), r["category"]) for r in apps]:
        raise ValueError("Merged report records do not match assignment app order/categories")
    names = [r.app_name.casefold() for r in records]
    if len(names) != len(set(names)):
        raise ValueError("Merged dataset contains duplicate app names")

    new_reviews = read_csv(OUT / "scrapedo_manual_verification_import_ready.csv")
    legacy_reviews = read_csv(OUT / "manual_verification_sample.csv")
    check_reviews(raw, new_reviews, legacy_reviews)
    metrics = analyze(raw, apps)
    metrics["source_attempt_status"] = Counter(a.get("status", "unknown") for r in raw for a in r.get("source_attempts", []))
    merge = merge_stats(raw)
    current_quality, readable_apps, source_url_count, retrieved_evidence_count = evidence_recheck(raw)
    metrics["app_research_status"] = dict(status_counters(raw))
    metrics["current_excerpt_quality"] = dict(current_quality)
    metrics["unique_evidence_source_urls"] = source_url_count
    metrics["retrieved_evidence_records"] = retrieved_evidence_count
    metrics["human_review_samples"] = {
        "scrapedo_20_claim_sample": dict(review_summary(new_reviews)),
        "original_v2_15_claim_sample": dict(review_summary(legacy_reviews)),
    }
    metrics["merge_summary"] = {
        key: value for key, value in merge.items()
        if key not in {"attempt_status", "conflict_fields"}
    }
    metrics["merge_summary"]["conflicting_fields_by_app"] = merge["conflict_fields"]
    merge_audit = (OUT / "merge_audit.md").read_text(encoding="utf-8")
    error_analysis = (OUT / "human_verification_error_analysis.md").read_text(encoding="utf-8")
    page = make_html(raw, apps, metrics, new_reviews, legacy_reviews, merge, merge_audit, error_analysis)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / "analysis.json").write_text(json.dumps({
        key: dict(value) if isinstance(value, Counter) else value for key, value in metrics.items()
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # GitHub Pages currently serves the repository-root homepage. Keep it in
    # sync with the self-contained report generated under output/.
    shutil.copyfile(OUT / "index.html", ROOT / "index.html")

    status_counts = status_counters(raw)
    _, usable_apps, unique_urls, _ = evidence_recheck(raw)
    review_counts = review_summary(new_reviews)
    print(f"Validated and rendered {len(records)} merged app records.")
    print("Research status: " + ", ".join(f"{key}={status_counts[key]}" for key in ("researched", "partial", "blocked", "not_researched")))
    print(f"Current classifier: {usable_apps} apps with retrieved readable evidence; {sum(len(r.get('evidence', [])) for r in raw)} evidence records / {unique_urls} unique evidence URLs.")
    print(f"Scrape.do human sample: {len(new_reviews)} claims; supported={review_counts['supported']}, unsupported={review_counts['unsupported']}, unclear={review_counts['unclear']}.")
    print(f"Wrote {OUT / 'index.html'}, {ROOT / 'index.html'}, and {OUT / 'analysis.json'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
