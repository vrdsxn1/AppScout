# AppScout

AppScout assesses the integration readiness of the 100 software applications in the Composio Product Operations Intern take-home assignment. It organizes sourced research on APIs, authentication, access requirements, MCP availability, limitations, and blockers, then presents the findings in a self-contained report.

## Final deliverables

- `output/research_results_merged.json` is the authoritative 100-app dataset in assignment order. It merges the original research with the later Scrape.do research while retaining original evidence and review metadata.
- `output/index.html` is the final report. The repository-root `index.html` is its GitHub Pages entry point; both are generated from the same dataset.
- `output/analysis.json` contains machine-readable report summaries.
- `output/merge_audit.md` documents per-app merge decisions and provenance.
- `output/human_verification_error_analysis.md` describes observed weaknesses in the reviewed claims and the classifier changes.
- `output/scrapedo_manual_verification_sample.csv` preserves the completed review worksheet; `output/scrapedo_manual_verification_import_ready.csv` is the normalized import copy used to apply the same reviewer verdicts and notes.

## Findings and limits

The report calculates 13 researched, 33 partially researched, 14 blocked, and 40 not-researched app records. These labels describe the available records; they do not mean every field of a researched app is complete. The current local excerpt classifier identifies readable evidence for 52 apps across 356 evidence records and 225 distinct URLs. Readable or `usable` evidence is not proof that a claim is correct; automated claim status and human verdicts are displayed separately.

The later Scrape.do sample contains 20 manually reviewed claims: 12 supported, 7 unsupported, and 1 unclear. The original 15 manually supported claims across Salesforce, HubSpot, and Pipedrive are also retained. These are small review samples, not overall accuracy estimates. The full app list is present, but research remains incomplete. In particular, Scrape.do explicitly disallowed the Stripe API documentation URL used in the smoke test; that URL was not retried. Blocked, unknown, unverified, and not-researched states remain distinct.

## Rebuild the report

Python 3.11 or newer and the dependencies in `requirements.txt` are sufficient for local validation and report generation. From the project root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/build_report.py
```

The build validates all 100 records against the Pydantic schema and regenerates `output/index.html`, root `index.html`, and `output/analysis.json` from `output/research_results_merged.json`. It does not make network requests. Open the report locally with:

```powershell
Start-Process .\output\index.html
```

The report embeds its CSS and JavaScript and works offline. Opening evidence links requires an internet connection.

## Local validation and review workflow

These commands run local checks only:

```powershell
python scripts/test_merge_research_datasets.py
python scripts/test_evidence_quality.py
python scripts/test_reviewed_evidence_quality.py
python scripts/test_scrapedo_verification.py
python scripts/verify_scrapedo_sample.py
python -m compileall -q appscout scripts
```

The verification command is read-only unless `--apply` is supplied. It keeps automated evidence quality and claim status separate from human verdicts. The report builder also checks that the 100-app order, the original 13 records and 15 supported claims, and the 20 Scrape.do review results remain represented.

## Optional public-page fetcher

The Scrape.do fetcher is optional and is not needed to build or view the submission. It uses the token in the project-root `.env` as `SCRAPEDO_API_TOKEN`; `.env` is ignored by Git. To install its separate dependencies and manually run the three-URL smoke test:

```powershell
python -m pip install -r requirements-research.txt
python scripts/smoke_test_scrapedo.py
```

The test is not run by validation or report generation. `scripts/test_scrapedo.py <URL>` tests one URL. Research runs use official/public URL seeds, robots checks, request spacing, timeouts, a local cache, incremental saves, and bounded controls such as `--limit` and `--render`. Do not use the fetcher to bypass logins, paywalls, rate limits, or source access restrictions. Retrieved text does not automatically support a claim. Legacy Firecrawl scripts remain for project history; the final report workflow does not depend on Firecrawl.

## Project map

| Path | Purpose |
| --- | --- |
| `data/apps.csv` | Exact assignment app names, categories, source URL, and order |
| `appscout/models.py` | Pydantic models for app records and evidence |
| `appscout/evidence_quality.py` | Conservative local excerpt-quality checks |
| `appscout/analytics.py` | Coverage and descriptive pattern summaries |
| `appscout/verification.py` | Human worksheet validation and verdict import helpers |
| `appscout/scrapedo_client.py` | Optional Scrape.do HTTP adapter |
| `scripts/merge_research_datasets.py` | Reproducible merge and preservation checks |
| `scripts/build_report.py` | Builds the report and analysis from the merged dataset |
| `scripts/run_free_research.py` | Optional, incremental public-page research runner |
| `output/research_results_merged.json` | Final authoritative research dataset |
| `output/index.html` | Self-contained final case study |
