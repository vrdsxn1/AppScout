# Manual verification guide

This worksheet contains 15 selected claims: five each for Salesforce, HubSpot, and Pipedrive. It intentionally includes claims with incomplete or potentially ambiguous excerpts, not only claims that appear well supported.

The `claim_supported` column is the pipeline's current status. All entries are `unverified`: the pipeline retrieved the page and stored a title/excerpt, but it did not make a human judgment about whether the page proves the claim. A retrieved page is not the same as a verified claim.

## How to review each row

1. Open the `evidence_url` in a browser. Confirm the page is available and is the source named by `source_title`.
2. Find the relevant section in the page. Compare the page's actual content with the entire `claim`, not only the `retrieved_excerpt`.
3. Check whether the page directly supports every part of the claim. Pay special attention to editions, plans, subscriptions, scopes, versions, quotas, rollout status, and date-sensitive labels.
4. Look for missing qualifications, contradictory statements, or claims that go beyond the source. The stored excerpt is a retrieval aid and may be incomplete; it is not itself a support verdict.
5. Enter exactly one `human_verdict` value from the list below. Use `reviewer_notes` to record the relevant page section, missing qualifier, contradiction, or reason the source could not be reached. Leave the source fields unchanged.

## Human verdict options

- `supported` — the inspected page directly supports the full claim, including material qualifications.
- `partially_supported` — the page supports only part of the claim or omits a material qualification.
- `unsupported` — the page does not support the claim, or it contradicts the claim.
- `source_unavailable` — the evidence page cannot be opened or inspected.
- `unclear` — the page is accessible, but its meaning or applicability cannot be determined confidently.

Do not infer a verdict from URL relevance, page title, retrieved status, or excerpt alone. Record observations in `reviewer_notes`; do not calculate accuracy from this sample at this stage.
