# AppScout human verification: error analysis

## Scope and method

This analysis matches all 20 rows in `scrapedo_manual_verification_import_ready.csv` to evidence records in `research_results_scrapedo.json` by app, field, claim, and URL. The original completed `scrapedo_manual_verification_sample.csv` remains the reviewer-owned source file; this analysis uses its import-ready copy, which fixes one misspelled verdict and restores one damaged excerpt cell while preserving every verdict and reviewer note.

The sample outcomes are 12 supported, 7 unsupported, 1 unclear, 0 partially supported, and 0 source unavailable. This was a small, stratified sample that intentionally included borderline excerpts. These counts describe this sample only. They are not statistically representative and are not an overall accuracy estimate.

The failures below are classified from the stored claim, excerpt, URL/title, source type, and reviewer note. No page was fetched during this analysis. No source is called outdated or inaccessible without evidence for that conclusion.

## Unsupported and unclear claims

### Pumble — Communications and Messaging

- **Field:** `access_model`
- **Claim:** “The pricing/access page states: - Meta: charset: utf-8 - Meta: name: viewport, content: width=device-width, initial-scale=1, shrink-to-fit=no - Meta: http-equiv: x-ua-compatible, content: ie=edge - Title: Pricing - Pumbleâ¢ - Meta: name: description, content: Affordable plans. Quick & easy setup. No hidden fees. - Meta: name: image, content: https://pumble.com/assets/images/pumble-og.png - Meta: name: application-name, content: Pumble - Meta: itemprop: name, content: Pricing - Pumbleâ¢ - Meta: itemprop: description, content: Affordable plans…”
- **Human verdict / note:** `unsupported` — “excerpt has meta not the exact data”
- **Source:** [Plans & Pricing](https://pumble.com/pricing#AF) (`pricing/access page`)
- **Stored excerpt:** “- Meta: charset: utf-8 / - Meta: name: viewport, content: width=device-width, initial-scale=1, shrink-to-fit=no / - Meta: http-equiv: x-ua-compatible, content: ie=edge / - Title: Pricing - Pumbleâ¢ / - Meta: name: description, content: Affordable plans. Quick & easy setup. No hidden fees. / - Meta: name: image, content: https://pumble.com/assets/images/pumble-og.png / - Meta: name: application-name, content: Pumble / - Meta: itemprop: name, content: Pricing - Pumbleâ¢ / - Meta: itemprop: description, content: Affordable plans.…”
- **Failure classification:** metadata/page shell; pricing information itself was not extracted. The excerpt does not establish plans, prices, eligibility, or API access terms.

### Google Ads — Marketing, Ads, Email and Social

- **Field:** `mcp_status`
- **Claim:** “The page documents this MCP capability: - [Google Ads MCP server](http://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server) - [Google Ads API AI agent skills](http://developers.google.com/google-ads/api/docs/developer-toolkit/agent-skills) - [](http://developers.google.com)”
- **Human verdict / note:** `unsupported` — “excerpt is very unclear”
- **Source:** [Google Ads Query Language overview](https://developers.google.com/google-ads/api/docs/query/overview) (stored title: “Google Ads Query Language”; `MCP documentation`)
- **Stored excerpt:** “- [Google Ads MCP server](http://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server) / - [Google Ads API AI agent skills](http://developers.google.com/google-ads/api/docs/developer-toolkit/agent-skills) / - [](http://developers.google.com)”
- **Failure classification:** navigation/index links, with a claim-to-source mismatch. The excerpt points to an MCP page but contains no details about an MCP integration. The source URL is a query-language overview, not the linked MCP page.

### BigCommerce — Ecommerce

- **Field:** `api_type`
- **Claim:** “The documentation describes a GraphQL API surface.”
- **Human verdict / note:** `unsupported` — “excerpt has meta not the exact data”
- **Source:** [Getting Started](https://developer.bigcommerce.com/developer/docs/admin/getting-started) (`API/developer documentation`)
- **Stored excerpt:** “- Meta: charset: UTF-8 / - Meta: name: viewport, content: width=device-width, height=device-height, initial-scale=1, minimum-scale=1, maximum-scale=5, user-scalable=yes / - Title: Getting Started | BigCommerce Docs / - Meta: name: fern-docs-build, content: {\"renderer\":\"static\",\"version\":\"1.1.3\",\"revision\":\"534ba282\",\"buildId\":\"01a20595-ebf1-7007-95af-9fe58397f848\"} / - Meta: name: description, content: Manage your store's data and operations programmatically through BigCommerce's REST and GraphQL APIs. / - Meta: …”
- **Failure classification:** metadata/page shell. Although the metadata description names REST and GraphQL, the reviewed excerpt is not API documentation body text and gives no GraphQL scope or limits. The reviewer specifically identifies the metadata problem.

### Magento (Adobe Commerce) — Ecommerce

- **Field:** `api_type`
- **Claim:** “The documentation describes a REST API surface.”
- **Human verdict / note:** `unsupported` — “no retrieved excerpt”
- **Source:** [REST endpoints for Adobe Commerce as a Cloud Service](https://developer.adobe.com/commerce/webapi/reference/rest/saas) (`API/developer documentation`)
- **Stored excerpt:** “- Title: REST endpoints for Adobe Commerce as a Cloud Service / - Meta: name: description, content: Review comprehensive reference documentation for the Adobe Commerce as a Cloud Service REST API schema. / - Meta: name: keywords, content: REST / - Meta: property: og:title, content: REST endpoints for Adobe Commerce as a Cloud Service / - Meta: property: og:description, content: Review comprehensive reference documentation for the Adobe Commerce as a Cloud Service REST API schema. / - Meta: property: og:url, content:…”
- **Failure classification:** missing documentation body text/page shell, as stated by the reviewer. The title and metadata mention REST, but the excerpt does not provide the promised reference content. **Hypothesis, not established cause:** the cited path is specifically for Adobe Commerce as a Cloud Service, so edition/version scope may also need qualification if the app-level claim is broader.

### Apify — Data, SEO and Scraping

- **Field:** `blockers`
- **Claim:** “The documentation states this access or usage qualification: statustypemessage400`invalid-request`POST data must be a JSON object400`invalid-value`Invalid value provided: Comments required400`invalid-record-key`Record key contains invalid character401`token-not-provided`Authentication token was not provided404`record-not-found`Store was not found429`rate-limit-exceeded`You have exceeded the rate limit of ... requests per second405`method-not-allowed`This API endpoint can only be accessed using the following HTTP methods: OPTIONS, POST”
- **Human verdict / note:** `unsupported` — “wrong retrieved excerpt”
- **Source:** [Apify API v2](https://docs.apify.com/api/v2/) (`API/developer documentation`)
- **Stored excerpt:** “statustypemessage400`invalid-request`POST data must be a JSON object400`invalid-value`Invalid value provided: Comments required400`invalid-record-key`Record key contains invalid character401`token-not-provided`Authentication token was not provided404`record-not-found`Store was not found429`rate-limit-exceeded`You have exceeded the rate limit of ... requests per second405`method-not-allowed`This API endpoint can only be accessed using the following HTTP methods: OPTIONS, POST”
- **Failure classification:** flattened status/error table and wrong excerpt, per reviewer. Row boundaries, endpoint association, and explanation are lost. The generated claim also lumps validation errors, authentication errors, not-found responses, rate limits, and HTTP method constraints together as general “blockers”; this is overbroad for integration readiness.

### Devin — AI, Research and Media-native

- **Field:** `access_model`
- **Claim:** “The pricing/access page states: - Meta: charset: utf-8 - Meta: name: viewport, content: width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no - Meta: name: next-size-adjust - Title: Plans and Pricing | Devin - Meta: name: description, content: Choose the perfect plan for your Devin journey. Free, Pro, Max, Teams, and Enterprise plans available. - Meta: property: og:title, content: Plans and Pricing | Devin - Meta: property: og:description, content: Choose the perfect plan for your Devin journey. Free, Pro, Max, Teams, and…”
- **Human verdict / note:** `unsupported` — “excerpt has meta not the exact data”
- **Source:** [Devin Plans and Pricing](http://devin.ai/pricing) (`pricing/access page`)
- **Stored excerpt:** “- Meta: charset: utf-8 / - Meta: name: viewport, content: width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no / - Meta: name: next-size-adjust / - Title: Plans and Pricing | Devin / - Meta: name: description, content: Choose the perfect plan for your Devin journey. Free, Pro, Max, Teams, and Enterprise plans available. / - Meta: property: og:title, content: Plans and Pricing | Devin / - Meta: property: og:description, content: Choose the perfect plan for your Devin journey. Free, Pro, Max, Teams, and…”
- **Failure classification:** metadata/page shell. Metadata names tiers but does not provide their actual terms, eligibility, or access requirements. The human note explicitly rejects the metadata excerpt as the exact evidence.

### Plaid — Finance and Fintech

- **Field:** `mcp_status`
- **Claim:** “The page documents this MCP capability: Hi! I'm Bill! You can ask me all about the Plaid API. Try asking questions like:Pssst -- I also moonlight as your IDE's research librarian! Plug me in via the [Plaid MCP Server](https://github.com/plaid/ai-coding-toolkit/tree/main/sandbox).”
- **Human verdict / note:** `unclear` — “not sure retrieved excerpt is from the app but looks relatable”
- **Source:** [Plaid API documentation](https://plaid.com/docs/api/#api-host) (stored title: “API”; `MCP documentation`)
- **Stored excerpt:** “Hi! I'm Bill! You can ask me all about the Plaid API. Try asking questions like:Pssst -- I also moonlight as your IDE's research librarian! Plug me in via the [Plaid MCP Server](https://github.com/plaid/ai-coding-toolkit/tree/main/sandbox).”
- **Failure classification:** ambiguous source context, as stated by reviewer. The excerpt contains a Plaid MCP link, but the stored text alone does not establish whether it is page content, documentation assistant/widget copy, or a supported official integration statement. The source URL is Plaid's API docs, but the linked repository's status was not inspected here. No stronger explanation is established.

### Grain — AI, Research and Media-native

- **Field:** `access_model`
- **Claim:** “The pricing/access page states: - Meta: charset: utf-8 - Title: Pricing | Grain - Meta: content: Free forever for individuals. Pro for power users. Business for teams that share meeting memory and AI., name: description - Meta: content: Pricing | Grain, property: og:title - Meta: content: Free forever for individuals. Pro for power users. Business for teams that share meeting memory and AI., property: og:description - Meta: content: https://cdn.prod.website-files.com/5f5e90c17e7c9eb95c7acb17/62482f87d89252065171022f_Grain%20Pricing.jpg,…”
- **Human verdict / note:** `unsupported` — “excerpt has meta not the exact data”
- **Source:** [Grain Pricing](http://grain.com/pricing) (`pricing/access page`)
- **Stored excerpt:** “- Meta: charset: utf-8 / - Title: Pricing | Grain / - Meta: content: Free forever for individuals. Pro for power users. Business for teams that share meeting memory and AI., name: description / - Meta: content: Pricing | Grain, property: og:title / - Meta: content: Free forever for individuals. Pro for power users. Business for teams that share meeting memory and AI., property: og:description / - Meta: content: https://cdn.prod.website-files.com/5f5e90c17e7c9eb95c7acb17/62482f87d89252065171022f_Grain%20Pricing.jpg,…”
- **Failure classification:** metadata/page shell. The excerpt contains pricing-marketing metadata but no plan details or API access conditions. The reviewer note explicitly says the excerpt is metadata rather than the exact data.

## Comparison with the 12 supported claims

All 20 sampled source hosts are first-party product or developer-documentation hosts; this sample does not compare first-party sources against third-party sources. Among the 12 supported rows, source types were 8 authentication-documentation entries, 3 API/developer-documentation entries, and 1 MCP-documentation entry. The eight failed/unclear rows comprised 3 pricing/access pages, 3 API/developer-documentation entries, and 2 MCP-documentation entries.

The supported sample includes relatively direct procedural prose, such as Klaviyo's private API-key instructions, Apify's bearer-token instructions, and Coda's MCP-server guidance. The clearest failures are instead machine-extracted metadata (Pumble, BigCommerce, Magento, Devin, Grain), a list of links without explanatory text (Google Ads), and a flattened error table (Apify blockers). That points to extraction structure and source-to-claim mapping as concrete failure modes.

Field counts in this intentionally selected sample:

| Field | Supported | Unsupported | Unclear |
|---|---:|---:|---:|
| `auth_methods` | 8 | 0 | 0 |
| `access_model` | 0 | 3 | 0 |
| `api_type` | 0 | 2 | 0 |
| `blockers` | 3 | 1 | 0 |
| `mcp_status` | 1 | 1 | 1 |

This is descriptive of the chosen 20 claims, not evidence that these rates generalize. Several supported entries still have apparent field/context weaknesses in their stored excerpt—for example, Sentry's rate-limit identity text is mapped to `auth_methods`, Shopify's excerpt warns against reusing access tokens but does not enumerate auth methods, and Telegram's excerpt is a changelog. Those remain human-supported as recorded; their presence shows that verdict and field-mapping quality must remain separate dimensions.

## Pipeline improvements

1. **Reject metadata-heavy excerpts as page shells.** The five pricing/API cases above were all metadata-dominated but labelled `usable`. The local classifier now flags repeated `Meta:`, `Title:`, and related metadata lines as `page_shell`.
2. **Reject linked index lists without prose.** Google Ads' three-link list is now `navigation`, not usable content. A link to an MCP page can seed a separate source fetch, but it cannot substantiate MCP behavior by itself.
3. **Flag flattened status tables.** Apify's `status type message` sequence and repeated HTTP statuses is now `insufficient` when structure and endpoint context have been lost. The runner should not present a mixed error-code index as a single integration blocker.
4. **Keep readability distinct from claim support.** These checks only set `evidence_quality`; they never set `claim_supported` or `human_verdict`. The Plaid row remains readable (`usable`) even though its human verdict is `unclear`, demonstrating why readable prose is not proof.
5. **Add source-to-claim and field relevance review before inference.** Apify blockers combines several error categories; Google Ads cites a query overview while quoting links to a different MCP page; Sentry's auth field is paired with rate-limit text even though it was human-supported. A deterministic keyword rule would risk rewriting meaning. This semantic change is recommended for a separate proposal or reviewer-facing warning, but is not implemented here.
6. **Preserve narrow scope and unknowns.** The Magento URL identifies Adobe Commerce as a Cloud Service, while the app-level label is broader. Future claims should carry edition/version restrictions only when explicit source text establishes them. Do not infer outdated, inaccessible, preview, or access-blocked status from missing body text; use `unknown`/`unverified` until evidence is retrieved.

## Safe implementation and limits

`appscout/evidence_quality.py` now detects the specific metadata, navigation-list, and flattened status-table patterns observed above. `scripts/test_reviewed_evidence_quality.py` exercises the actual reviewed records as regression examples, including Plaid as a readable-but-unclear control. The checks do not make web requests and do not edit any research record. Existing imported human verdicts, reviewer notes, automated `claim_supported` values, and the original v2 review remain unchanged.

The classifier remains a conservative format/readability check. It cannot decide whether a readable excerpt semantically supports a claim, whether a whole page qualifies a claim, or whether a linked target is official/current. Those questions require claim-level source review.
