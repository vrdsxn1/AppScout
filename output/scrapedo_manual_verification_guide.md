# Scrape.do manual verification guide

This worksheet contains a 20-claim sample from evidence added to `research_results_scrapedo.json`. It is separate from the original Salesforce, HubSpot, and Pipedrive worksheet and does not change its 15 reviewed entries.

## Review each row

1. Open the `evidence_url` and confirm that it is the expected official or public source.
2. Read the relevant page section, not only the stored excerpt. Check whether it directly supports the complete `claim` for the named `field` and app.
3. Note missing qualifications, scope, plan restrictions, version differences, or contradictions in `reviewer_notes`.
4. Choose one `human_verdict`: `supported`, `partially_supported`, `unsupported`, `source_unavailable`, or `unclear`.

The excerpt and `evidence_quality` are aids for reading quality. A `usable` excerpt means that readable text was extracted; it does not mean the page supports the claim. `claim_supported` is the pipeline's separate automated status and should not be edited as a human result. Leave a verdict blank until that row has been reviewed.

Some rows were selected because their `usable` excerpts may be metadata, navigation, or otherwise weakly relevant. This helps test whether manual review catches false positives in the readability classifier.

## Validate and import completed reviews

From the project root, first run a read-only check:

```powershell
python scripts/verify_scrapedo_sample.py
```

After filling verdicts and notes, validate and apply nonblank verdicts to the exact matching evidence records in `output/research_results_scrapedo.json`:

```powershell
python scripts/verify_scrapedo_sample.py --apply
```

The importer verifies app, category, field, claim, URL, excerpt, and automated statuses before writing. It changes only `human_verdict` and `review_method` for exact matches; it does not infer a review date, change automated statuses, or touch the original worksheet, baseline data, v2 file, or website. The summary describes this sample only and is not overall accuracy.
