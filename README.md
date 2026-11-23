# AppScout

AppScout assesses how ready software applications are to integrate with AI agents. The project records API and authentication details, access requirements, MCP availability, integration blockers, and source evidence for the 100 applications in the Composio take-home assignment.

## Submission status

All 100 assignment apps have an ordered record in `output/research_results_free.json`. This is **record coverage**, not complete research coverage:

- 46 of 100 apps have at least one readable evidence excerpt (13 existing records plus 33 records with excerpts from the free public-page pass).
- The 33 new records with evidence are marked partial; 14 are blocked and 40 have no usable research from that pass. New-app statuses sum to 87.
- A readable excerpt means only that text was retrieved and passed a local readability check. It does not establish that every associated claim is true. New claims remain unverified.
- The original 13 records and their evidence are preserved unchanged from `output/research_results_v2.json`.
- The human review covered 15 claims across Salesforce, HubSpot, and Pipedrive. All 15 were marked supported. This is a small manually reviewed sample, **not an overall accuracy rate**.
- The remaining 87 apps were attempted through free public pages without paid services. Firecrawl credits were exhausted, blocked pages and robots restrictions were respected, and no login, paywall, rate limit, or challenge was bypassed.

## Build and validate on Windows

Use Python 3.11 or newer. From the project root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/validate_app_list.py
python scripts/validate_project.py
python scripts/test_evidence_quality.py
python -m compileall -q appscout scripts examples
python scripts/build_report.py
```

`build_report.py` validates and summarizes local files, then rebuilds:

- `output/index.html` — self-contained, responsive case study. Open directly in a browser.
- `output/analysis.json` — machine-readable coverage and descriptive summaries.

To open the report:

```powershell
Start-Process .\output\index.html
```

The report embeds its CSS and JavaScript. It has no CDN or external runtime dependency, so the report itself works offline. Evidence links require an internet connection when opened.

## Data and provenance

- `data/apps.csv` contains the exact 100-app assignment list, categories, order, and assignment source URL.
- `output/research_results.json` is the original baseline; `output/research_results_v2.json` contains the first 13 researched records, including the 15 manually supported evidence entries.
- `output/research_results_free.json` contains all 100 records in assignment order. The first 13 records are preserved exactly from v2. Later records contain the results and access notes from the free public-page pass; unknown, blocked, and unverified values remain explicit.
- `output/manual_verification_sample.csv` is the completed 15-claim worksheet. `output/manual_verification_summary.md` describes its scope.
- `output/additional_manual_review_sample.csv` is an optional 15-claim worksheet drawn from readable excerpts in newly researched records. Its human verdict and reviewer notes are blank; it records no review outcomes.
- `output/expansion_quality_audit.md` documents weaknesses in the earlier ten-app expansion. `output/evidence_extraction_test.json` is the isolated Attio/Twenty extraction experiment and does not replace v2.
- `output/index_pre_expansion_backup.html` is a backup of the prior report.

Coverage and pattern summaries are descriptive. API/auth/access groupings and blocker themes use local categorization of stored text. Evidence readability is not claim verification. Report generation does not make network requests or modify the source research datasets or completed review worksheet.

## Free public-page fetcher

`requirements-research.txt` lists `requests` for the optional free fetcher. Install it only if you want to resume public-page collection:

```powershell
python -m pip install -r requirements-research.txt
python scripts/run_free_research.py --limit 1
```

The fetcher reads official-site URL seeds, obeys robots.txt, spaces requests by host, uses timeouts, does not retry HTTP 403/429, and saves after each attempted page. It resumes from `output/research_results_free.json`; use `--max-pages-per-app` to control the bounded pages per app. It does not need a Firecrawl key and does not guarantee a complete research record. Inspect the output and rebuild the report after a run.

Legacy Firecrawl scripts are retained for project history and are excluded from the final runnable workflow. Do not run them without available credits and explicit authorization.

## Project map

```text
appscout/models.py                    Pydantic schemas for app records and evidence
appscout/analytics.py                 Local coverage and pattern summaries
appscout/evidence_quality.py          Conservative excerpt readability classifier
data/apps.csv                        Assignment app list
scripts/run_free_research.py          Optional polite public-page reader
scripts/validate_app_list.py          Checks exact assignment list structure
scripts/validate_project.py           Checks record validity and preservation
scripts/test_evidence_quality.py      Offline classifier examples
scripts/build_report.py               Builds the report and analysis from local data
output/research_results_free.json     100 ordered app records
output/index.html                     Final self-contained case study
```

## Limitations

The 100-app list is complete, but the research is not. Many fields are unknown or unclear, and 54 apps lack evidence that meets the report's readable-excerpt coverage definition. The manually reviewed 15 claims are the only human-verification results reported. No overall accuracy metric is available. No Git remote or deployment configuration is present in this workspace, so the report is prepared locally and has not been published.
