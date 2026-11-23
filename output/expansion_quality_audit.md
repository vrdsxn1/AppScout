# Expansion quality audit: 10 additional AppScout records

**Scope:** Attio, Twenty, Podio, Zoho CRM, Close, Copper, DealCloud, Zendesk, Intercom, and Freshdesk in `output/research_results_v2.json`. This is a structural and stored-evidence audit only. No evidence URLs were opened and no web requests were made. Pydantic validity does not establish that a claim is true.

## Record and evidence inventory

| App | Pydantic valid | Evidence records | Unknown/unclear key fields |
|---|---:|---:|---|
| Attio | Yes | 10 | None explicitly marked |
| Twenty | Yes | 10 | None explicitly marked |
| Podio | Yes | 12 | None explicitly marked |
| Zoho CRM | Yes | 11 | None explicitly marked |
| Close | Yes | 11 | None explicitly marked |
| Copper | Yes | 11 | None explicitly marked |
| DealCloud | Yes | 11 | access_model |
| Zendesk | Yes | 9 | None explicitly marked |
| Intercom | Yes | 16 | None explicitly marked |
| Freshdesk | Yes | 11 | None explicitly marked |

All ten records validate against `AppResearchRecord`. None explicitly marked means the text does not contain an explicit unknown/unclear marker; it does not mean that evidence is complete. DealCloud's access model includes a stated unknown for public pricing/access availability, so it is flagged as unknown.

## Evidence gaps and excerpt quality

The model stores evidence records separately from summary fields and does not link individual field values to evidence IDs. Consequently, a URL attached to a related claim cannot be assumed to support every detail in a long summary field. Based on the stored claims/excerpts, the following issues need attention:

### Attio

- Authentication, rate-limit, and MCP tool-list claims point to excerpts that are serialized Mintlify page configuration (`docsConfig`), not the quoted facts. The pricing excerpt only says Start for free; it does not establish the three-user limit, 14-day Pro trial, or all named paid tiers.
- API breadth and MCP status summarize many operations; the stored excerpts for the detailed lists are page-shell text, so the breadth is not demonstrated by these excerpts.

### Twenty

- Most API, OAuth, pricing-plan, and MCP claims have excerpts that are serialized page configuration, not the asserted documentation. The pricing-page excerpt supports Pro/Organization prices, but not the separate Cloud trial assertion.
- The broad MCP tool list and REST/GraphQL capability summary need usable excerpts showing scope and qualifications.

### Podio

- The MCP entry says the server is beta and that shared credentials are limited to roughly 30-40 requests, but the stored excerpt only describes shared credentials and does not show either the beta label or request limit. The claim therefore needs narrower wording or a relevant excerpt.
- The API-reference inventory excerpt is navigation, and the scope excerpt is only a short example token string; neither demonstrates the full listed surface/scope taxonomy.

### Zoho CRM

- Several API/reference and MCP claims use navigation/changelog excerpts rather than the asserted API details. The record's forever-free/API-access and edition limits should be tied to exact pricing/access evidence; the pricing/access claim is not directly evidenced by a clear excerpt in the record.
- MCP tool families and OAuth client support need direct excerpts that show both the server availability and supported operations/client constraints.

### Close

- The API breadth has a useful qualification: its OpenAPI specification is explicitly experimental and incomplete. Preserve that caveat. The stored pricing excerpt is a feature table snippet and does not visibly show the claimed 14-day trial or Essentials API quota wording; those details need a relevant excerpt.

### Copper

- The required-header excerpt supports those header names. The OAuth excerpt supports the `developer/v1/all` scope but does not support the separate claim that registration requires contacting `partners@copper.com`; obtain a matching excerpt or narrow that claim. The MCP beta timing and read-only scope do have direct excerpts; keep their November 2026 timing and waitlist qualification attached.

### DealCloud

- The rate-limit excerpt is a table; confirm the summary preserves per-area endpoint distinctions. The MCP requirements excerpt shows license/capability gates, but broad claims about all exposed schema/tools and local-client enablement should remain separately qualified. Public access/pricing is explicitly unknown and should stay unknown.

### Zendesk

- The pricing excerpt is feature copy, not the stated $19 price/trial; that access/pricing claim lacks direct excerpt support. The rate-limit excerpt shown begins with an endpoint-specific exception, not the broad 200-2,500 plan range. The MCP client and MCP server are distinct roles and the summary should keep client GA separate from Bridge server EAP.

### Intercom

- The API reference excerpt is navigation, not proof of the full resource inventory/version. The conversation-scope excerpt is only a heading, so it does not state the limit. Pricing excerpt proves a 14-day trial link but not paid-seat or Fin pricing details. The MCP authentication excerpt discusses dynamic registration/allowlisting and does not itself prove bearer-token support; preserve region and Fin Operator eligibility limits.

### Freshdesk

- The authentication excerpt is an unrelated custom-mailbox attribute table, not API-key Basic Auth. The resource-list excerpt is navigation, not the broad endpoint inventory. The pricing excerpt supports Enterprise $89 only; it does not support Growth/Pro prices, trial, or MCP add-on fee. The MCP excerpt about GA date/plans/actions is an EAP migration note and does not clearly support the summary's GA assertion; inspect status wording manually before retaining it.

## URL checks

All evidence URLs in these ten records parse as HTTP or HTTPS URLs; no malformed or non-HTTP(S) URLs were found. Repeated URLs occur within a record where one source is cited for multiple separate claims; this is not inherently invalid, but each repeated claim still needs its own relevant excerpt. Repeated URL counts:

- **Attio:** 2 repeated URL(s): `https://docs.attio.com/rest-api/guides/authentication`, `https://docs.attio.com/mcp/overview`
- **Twenty:** 2 repeated URL(s): `https://docs.twenty.com/developers/extend/api`, `https://docs.twenty.com/user-guide/ai/capabilities/mcp`
- **Podio:** 1 repeated URL(s): `https://www.progress.com/podio/documentation/using-podio/ai-and-mcp/podio-mcp-server-integration-guide`
- **Zoho CRM:** 3 repeated URL(s): `https://www.zoho.com/crm/developer/docs/api/v8/api-references.html`, `https://www.zoho.com/crm/developer/docs/api/v8/api-limits.html`, `https://www.zoho.com/crm/developer/docs/mcp/overview.html`
- **Close:** 2 repeated URL(s): `https://developer.close.com/api/overview`, `https://developer.close.com/mcp`
- **Copper:** 3 repeated URL(s): `https://developer.copper.com/introduction/requests.html`, `https://developer.copper.com/introduction/oauth/index.html`, `https://www.copper.com/mcp`
- **Intercom:** 4 repeated URL(s): `https://developers.intercom.com/docs/build-an-integration/learn-more/authentication`, `https://www.intercom.com/help/en/articles/9071694-intercom-developer-faqs`, `https://developers.intercom.com/docs/build-an-integration/learn-more/authentication/oauth-scopes`, `https://developers.intercom.com/docs/guides/mcp`
- **Freshdesk:** 1 repeated URL(s): `https://support.freshdesk.com/support/solutions/articles/50000012670-model-context-protocol-mcp-integration-in-freshdesk-eap-`

No malformed URLs were found. Duplicate URLs are limited to these within-record citations: Attio (2 URLs, each used twice), Twenty (2, each twice), Podio (1, twice), Zoho CRM (3, repeated), Copper (3 repeated URLs), Intercom (4, repeated), and Freshdesk (1, twice). The assignment URL is also reused across apps as a shared category source.

## Similarity and possible copying

No obvious verbatim cross-app copying was identified in the app-specific summaries from this audit. The common assignment-list evidence excerpt is expected to recur across all apps. Several records do share the same weakness pattern: long summaries paired with generic navigation/page-shell excerpts, so the similarity is more consistent with a retrieval/excerpt-extraction problem than evidence of copied app facts. Similarity was assessed by comparing stored summary/evidence wording and source targets, not by semantic web verification.

## Fix before scaling

- Fix page extraction for documentation sites that currently store serialized page configuration or navigation instead of readable body text; treat these excerpts as unusable for claim support.
- Require a field-to-evidence mapping (or claim IDs) and reject or flag high-impact summary details without a specific supporting excerpt.
- Preserve qualifications for pricing, trial eligibility, API plan gates, rate limits, MCP deployment regions, EAP/beta/GA status, and read/write scope. A source excerpt about one qualification should not be stretched to support adjacent details.
- Make unverified remain distinct from model validity and retrieval success; these records are structurally valid, but stored excerpt quality is uneven.
- Keep unknown access/pricing facts explicit (including DealCloud) and avoid treating high confidence as a substitute for direct evidence.

**No evidence was marked verified in this audit. No accuracy metrics were calculated.**
