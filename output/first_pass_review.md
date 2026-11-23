# AppScout first-pass research review

**Scope:** reviewed the three records in `research_results.json` and the Pydantic models in `appscout/models.py`. Each evidence URL below is grouped with the claim stored beside it. “Supported” means the page content inspected directly supports the stated part of the claim. “Partial” means the page supports only part of the wording or misses a material qualifier. A valid URL by itself is not treated as support.

**Retrieval note:** Firecrawl successfully returned page content for the first ten unique URLs, then returned HTTP 429 for subsequent requests. Additional vendor pages were inspected through page retrieval where accessible. The assignment page returned 429 during this audit; it had been retrieved when the app list was imported, but is marked as not re-fetched here. A claim marked unsupported is not necessarily false; it needs better evidence or narrower wording.

No accuracy or verification metrics are calculated in this review.

## Salesforce — CRM and Sales

### Record fields

- **Description:** Salesforce provides REST and GraphQL APIs for accessing and manipulating Salesforce data, plus official hosted and developer MCP servers for AI clients.
- **Auth methods:** OAuth 2.0 through an External Client App or Connected App; for hosted MCP, OAuth scopes, PKCE, and JWT-based tokens.
- **Access model:** self-serve Developer Edition and free trials; production API access varies by edition/license; Professional needs an API add-on; user/admin permissions and OAuth app setup are required.
- **API type:** REST and GraphQL.
- **API breadth:** REST resources and GraphQL queries/mutations, with usage limits.
- **MCP status:** hosted MCP servers and Salesforce DX MCP; result labels DX MCP “Beta.”
- **Buildability:** `build_with_restrictions`.
- **Blockers:** org and API-enabled user; edition/add-on requirements; OAuth/scopes; API limits; administrator activation for hosted MCP.
- **Confidence:** `high` in the saved record. This is the agent’s confidence label, not a measured accuracy result; given the gaps below, it should be lowered or explained.

### Evidence by claim

1. **Claim:** REST API provides programmatic access and resources for metadata, CRUD, query, search, and limits. [REST API introduction](https://developer.salesforce.com/docs/platform/api-rest/guide/intro-rest.html) — **Partial.** The page says, “REST API provides you with programmatic access to your data in Salesforce.” The page introduces REST resources, but the recorded claim bundles multiple endpoint families and limits that should be supported with the specific reference pages, not just the introduction.
2. **Claim:** API access is enabled by default for Enterprise, Performance, Unlimited, and Developer; Professional can add it; users need `API Enabled`. [Supported editions and required permissions](https://developer.salesforce.com/docs/platform/api-rest/guide/intro-rest-compatible-editions.html) — **Supported.** The page states API access is enabled by default in those four editions and Professional can add it; it separately requires the `API Enabled` user permission. This supports edition/permission constraints, not that Developer Edition sign-up is free or available to every prospective builder.
3. **Claim:** REST clients use External/Connected Apps and OAuth 2.0; flows issue access and refresh tokens. [OAuth and Connected Apps](https://developer.salesforce.com/docs/platform/api-rest/guide/intro-oauth-and-connected-apps.html) — **Partial.** The inspected page directly says REST clients use an External Client App or Connected App and an OAuth 2.0 flow. It also says new Connected App creation is restricted as of Spring ’26. The result’s access/refresh-token wording should be tied to the particular flow documentation; do not imply all flows issue refresh tokens.
4. **Claim:** GraphQL is available in the listed editions and supports field selection, aggregation, schema introspection, and UI-API-enabled sObjects. [GraphQL introduction](https://developer.salesforce.com/docs/platform/graphql/guide/intro-graphql-api.html) — **Supported, with scope caveats.** The page says GraphQL is available in “Enterprise, Performance, Unlimited, and Developer editions” and lists field selection, resource aggregation, and schema introspection. It describes sObjects subject to object/field security. “Available in” does not mean every object/field is exposed, so those constraints should be prominent.
5. **Claim:** GraphQL documentation includes create, update, and delete record mutations. [GraphQL mutations introduction](https://developer.salesforce.com/docs/platform/graphql/guide/mutations-intro.html) — **Supported for the existence of those mutation operations.** The page links to separate “Create a Record,” “Delete a Record,” and “Update a Record” guides. The actual usable mutation set still depends on the documented object/schema permissions.
6. **Claim:** API concurrency and rolling 24-hour allocations include 15,000 calls for Developer Edition; extra capacity can be purchased or obtained through licenses. [API request limits and allocations](https://developer.salesforce.com/docs/platform/salesforce-app-limits-cheatsheet/guide/salesforce-app-limits-platform-api.html) — **Supported, with wording to tighten.** The table directly lists 15,000 total calls per 24 hours for Developer Edition and license-specific limits for other editions. The page also says orgs can buy additional user licenses or extra API calls. Keep the usage allocation, concurrency limits, and purchase options as distinct points rather than implying every org has the same allocation.
7. **Claim:** Sales pricing lists a free 30-day trial and a Web Services API line item at an additional $25/user/month. [Sales Cloud pricing](https://www.salesforce.com/sales/pricing/) — **Partial.** The page says Sales Cloud has a free 30-day trial and its comparison table shows “Additional $25 USD/user/month” for Web Services API. This does not establish that the trial includes API access, or that the add-on price applies to every edition or contract. The access-model sentence conflates trial availability with API entitlement.
8. **Claim:** Hosted MCP has SObject All/Reads/Mutations/Deletes servers, is disabled by default, and applies user permissions/security. [Hosted MCP server reference](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/references/reference/servers-reference.html) — **Partial.** The reference page lists standard server names including SObject All, Reads, Mutations, and Deletes. The disabled-by-default and authentication details are supported by the separate setup/activation pages below, not by this reference page alone.
9. **Claim:** Hosted MCP setup needs External Client App, OAuth scopes, PKCE/JWT, and System Administrator or equivalent access. [Hosted MCP setup overview](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/setup-overview.html) — **Supported.** The page requires PKCE and JWT-based security settings and System Administrator or equivalent permissions to create the External Client App.
10. **Claim:** Hosted MCP servers are disabled by default and an administrator must enable them. [Activate MCP servers](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/activate-mcp-servers.html) — **Supported.** The page says they are “disabled in your org by default” and must be enabled by an administrator.
11. **Claim:** Salesforce DX MCP is “Beta” and has more than 60 tools. [Salesforce DX MCP Server and Tools](https://developer.salesforce.com/docs/platform/sfdx-dev/guide/sfdx-dev-mcp.html) — **Partial.** The page says the server includes “over 60 MCP tools.” It describes IDE/developer tasks and local pre-existing org authentication. The page inspected does **not** label this server Beta. The “Beta” label is unsupported by the attached page, and DX MCP should be distinguished from hosted CRM-data MCP servers.
12. **Claim:** The assignment lists Salesforce in CRM and Sales. [Assignment source](https://composio.notion.site/AI-Product-Ops-Intern-The-take-home-assignment-391f261a6dfe80e9946bee899d3a3762) — **Not accessible in this audit (HTTP 429); previously inspected during app-list import.** Its earlier retrieved section heading was “CRM and Sales.” No current excerpt could be retrieved for this review.

### Missing, suspicious, or unsupported

- No cited source directly establishes that a self-serve Developer Edition is free and can be provisioned for this integration, nor that the listed free trial gives the required API access.
- The $25 API line item is a pricing-table detail, not a universal API access price. Its scope and trial applicability are unresolved.
- “Beta” for DX MCP is not supported by its cited source.
- The GraphQL summary omits important edition/object permission constraints. The REST summary should cite resource-specific references for each claimed operation family.
- Multiple blockers and access qualifications are supported across separate sources, but the record does not map each blocker to a source claim individually.

## HubSpot — CRM and Sales

### Record fields

- **Description:** date-versioned REST API, GraphQL for CRM/HubDB, and official remote MCP.
- **Auth methods:** OAuth 2.0; static access tokens for single-account/private apps.
- **Access model:** self-serve free tools and paid tiers; access/limits vary by distribution, subscription, scopes, and permissions.
- **API type:** REST and GraphQL.
- **API breadth:** described as broad; date-versioned REST across CRM/platform APIs and GraphQL for CRM/HubDB, with limits.
- **MCP status:** official remote CRM MCP and separate local developer MCP, with OAuth/PKCE and account-dependent tools.
- **Buildability:** `build_with_restrictions`.
- **Blockers:** OAuth backend for multi-account apps; private distribution cap; static auth single-account; rate limits; MCP scopes and permissions.
- **Confidence:** `high` in the saved record. Direct sources exist, but the GraphQL scope and REST classification need tighter wording; the confidence label is not a measured accuracy score.

### Evidence by claim

1. **Claim:** OAuth is for multi-account apps; static auth tokens are for one account/private apps. [Authentication overview](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/overview) — **Supported.** The page says OAuth is required for multiple accounts, while static auth is for a single authorized account; private OAuth distribution is capped at 10 allowlisted accounts. The record does not state the “OAuth backend” requirement in this evidence claim, though the page says developers must host one to initiate OAuth/manage tokens.
2. **Claim:** API reference has date-based versions, `api.hubapi.com`, and REST-style CRM endpoints. [2026-09 API reference overview](https://developers.hubspot.com/docs/api-reference/latest/overview) — **Partial.** The page explicitly shows date-versioned paths and `https://api.hubapi.com/`; it lists multiple product API families. The inspected page does not call the API “REST,” so the REST classification is inferred from endpoint shape rather than directly stated in this cited source.
3. **Claim:** GraphQL can query HubSpot CRM and HubDB data and be used in integrations. [Query HubSpot data using GraphQL](https://developers.hubspot.com/docs/cms/start-building/features/data-driven-content/graphql/query-hubspot-data-using-graphql) — **Partial.** The page explicitly describes CRM and HubDB data, and provides contact/query examples. It is framed around data-driven content/CMS experiences and subscription-dependent tools, not a general replacement for all CRM REST endpoints. It also documents a 500-item cap per CRM query and query-complexity limits; the saved breadth summary omits these significant limits.
4. **Claim:** Pricing page has free tools at $0/month/no card and paid Starter. [HubSpot CRM pricing](https://www.hubspot.com/pricing/crm) — **Supported for free tools and price.** The page lists Free foundational tools at `$0/mo`, “Free for up to 2 users,” and “No credit card required.” This proves account/product access to free tools, not that every API or MCP tool is enabled on the Free tier.
5. **Claim:** Official remote MCP uses a connector/OAuth/PKCE and supports read/write CRM capabilities subject to account permissions. [Remote HubSpot MCP integration guide](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server) — **Supported, with scope caveats.** The page requires an MCP connector and PKCE; it lists CRM read and write actions and says tool availability varies by subscription, user permissions, and account configuration. It also clearly distinguishes the remote CRM server from the separate local developer MCP server, so that part of the saved status is supported. Revenue-object functions are marked beta and some features require paid subscriptions/optional scopes.
6. **Claim:** Free/Starter private apps have 100 requests per 10 seconds per app and 250,000 per account per day. [API usage guidelines](https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines) — **Supported with distribution qualifier.** The page’s table gives these limits for privately distributed apps and states the burst limit is per app and the daily limit is shared by apps in an account. These numbers do not apply to every app distribution type; the saved blocker should retain “privately distributed.”
7. **Claim:** The assignment lists HubSpot in CRM and Sales. [Assignment source](https://composio.notion.site/AI-Product-Ops-Intern-The-take-home-assignment-391f261a6dfe80e9946bee899d3a3762) — **Not accessible in this audit (HTTP 429); previously inspected during app-list import.** No current excerpt could be retrieved for this review.

### Missing, suspicious, or unsupported

- REST is not explicit on the cited API overview page; cite the official REST API guide or use a more cautious `api_type` until directly checked.
- GraphQL is materially narrower and subscription-dependent compared with the general REST surface; “Broad” is vague and may overstate it. Include the documented 500 CRM items/query cap and complexity limits.
- “Free tools” does not establish broad API or MCP access on Free. Keep product-plan pricing separate from developer API access and MCP tool entitlements.
- Rate-limit figures apply to privately distributed apps; avoid presenting them as universal HubSpot limits.
- MCP access is tool-, subscription-, scope-, and permission-dependent; the saved description should distinguish available operations from guaranteed operations.

## Pipedrive — CRM and Sales

### Record fields

- **Description:** CRM with REST API for CRM data, sales processes, webhooks, and developer apps.
- **Auth methods:** API token and OAuth 2.0.
- **Access model:** paid SaaS with a free 14-day trial; API token/API access included in every plan.
- **API type:** REST.
- **API breadth:** many CRM resources; API v2 is rolling out gradually and covers a defined subset.
- **MCP status:** official native MCP for AI assistants, OAuth, CRM querying and actions, described as available on all plans.
- **Buildability:** `build_now`.
- **Blockers:** none listed.
- **Confidence:** `high` in the saved record. Most cited claims were directly supported, but a few breadth/auth details should be scoped. This label is not a measured accuracy score.

### Evidence by claim

1. **Claim:** API reference is REST/JSON, token-authenticated, and includes many CRM resources. [Pipedrive API reference](https://developers.pipedrive.com/docs/api/v1) — **Supported.** The reference says it is the “RESTful Pipedrive API,” uses JSON, and validates requests against an API token; its endpoint index lists activities, deals, leads, organizations, persons, products, projects, users, webhooks, and more.
2. **Claim:** A user obtains an API token manually from the Pipedrive app. [How to find the API token](https://pipedrive.readme.io/docs/how-to-find-the-api-token) — **Supported.** The page says a user’s API token identifies the account and that a user has a different token for each company. It also notes only one active token at a time. The record should distinguish an account token from OAuth for apps.
3. **Claim:** OAuth 2.0 is required for Marketplace apps and provides authorization/token flows. [OAuth documentation](https://developers.pipedrive.com/docs/api/v1/Oauth) — **Supported.** The page says OAuth 2.0 is necessary for Marketplace apps and links authorization, token, and refresh-token endpoints. Do not imply every direct API integration must use OAuth; the same reference supports API-token authentication.
4. **Claim:** Every plan includes a free API token and REST API access. [Pipedrive CRM API page](https://www.pipedrive.com/en/features/crm-api) — **Supported.** The page says “Every Pipedrive plan comes with an API token” and describes free REST API access. The word “free” applies to API access with the plan, not to the paid CRM subscription itself.
5. **Claim:** Pricing advertises a free 14-day trial with no card and paid plans. [Pipedrive pricing](https://www.pipedrive.com/en/pricing) — **Supported.** The page states “Free 14-day trial. No credit card required” and lists paid plans. Trial is temporary and distinct from ongoing API access.
6. **Claim:** API v2 is gradually replacing v1 and has a listed subset of resources. [Pipedrive API v2 overview](https://pipedrive.readme.io/docs/pipedrive-api-v2) — **Supported.** The page describes a “gradual transition” and lists v2 availability for activities, deals, fields, organizations, persons, products, pipelines/stages, followers, and search. It says corresponding v1 endpoints receive a deprecation grace period. The saved summary correctly says rollout is gradual, but should say the v2 list is a subset rather than imply full parity.
7. **Claim:** Official MCP uses secure OAuth and can query/update CRM records and workflows; available on all plans. [Pipedrive MCP page](https://www.pipedrive.com/en/features/mcp-server) — **Supported for the page’s product claims.** The page documents secure OAuth, searching CRM records, creating/updating deals/contacts/activities, and says all customers on every plan can use MCP; usage is subject to plan token limits. This is product-page evidence, so technical setup/tool details should also cite the linked MCP developer documentation if implementation depends on them.
8. **Claim:** Pipedrive built/maintains native MCP; supports ChatGPT, Claude/other tools, OAuth, and actions. [Native MCP announcement](https://www.pipedrive.com/en/newsroom/pipedrive-launches-native-mcp-server-bringing-crm-workflows-directly-into-ai-assistants) — **Supported for native/official status and basic actions.** The article says Pipedrive launched its native MCP server and describes searching deals/contacts/organizations/leads and creating/updating CRM records. Plan availability is better supported by the MCP feature page above than by this announcement.
9. **Claim:** Assignment category is CRM and Sales. [Assignment source](https://composio.notion.site/AI-Product-Ops-Intern-The-take-home-assignment-391f261a6dfe80e9946bee899d3a3762) — **Not accessible in this audit (HTTP 429); previously inspected during app-list import.** No current excerpt could be retrieved for this review.

### Missing, suspicious, or unsupported

- The sources support a broad v1 API, but Pipedrive API v2 is only gradually replacing v1 and currently covers a subset. Keep version scope visible.
- `blockers: []` means no blocker was recorded, not that access has no prerequisites. A Pipedrive account, account-specific API token or OAuth consent, and plan-based MCP token limits remain practical constraints.
- `build_now` is plausible for an API toolkit from the cited evidence, but define whether the verdict assesses building a custom toolkit or using the already available native MCP integration.
- “Broad” should be replaced with a bounded resource summary rather than a general label.

## Cross-record issues to fix before scaling

1. **Pydantic checks shape, not truth.** `AppResearchRecord` requires fields, dates, allowed buildability/confidence values, nonblank strings, and valid HTTP URLs. It does not check that a URL is reachable, official, current, or relevant; it does not link a claim to a field; it permits empty evidence and arbitrary `access_model`, `api_type`, and `mcp_status` text.
2. **Pipeline does not verify citations.** It validates the agent’s structured response and appends the assignment category citation, but it never scrapes each returned evidence URL or checks whether retrieved text supports each claim. “Validated record” currently means schema-valid, not fact-checked.
3. **Evidence needs field-level linkage.** The current `EvidenceRecord` has a free-text claim and URL. Add a simple `field`/`supports` key or require explicit claim-to-field mapping, then flag non-unknown fields without evidence.
4. **Prompt needs tighter scope and output rules.** Ask for one or two evidence-backed facts per field, direct page evidence, limiting conditions, and shorter summaries. For pricing, distinguish product pricing, API access add-ons, and the trial’s actual API entitlement. Distinguish public REST API, app authentication, and native MCP auth.
5. **Confidence and buildability need operational definitions.** “High” should require direct evidence for all material fields or be recalculated from evidence coverage. Specify what `build_now` means when an official MCP already exists, and treat missing blocker evidence as unknown rather than an empty “none.”
6. **Record retrieval failures and provenance.** Store retrieval time/status, page title, and a short excerpt or content hash for each source. Respect rate limits (the audit’s Firecrawl pass received HTTP 429 after ten URLs), retry with backoff, and label unavailable pages instead of silently treating search output as page inspection.

## Bottom line for this pass

The records contain several well-supported findings, especially Pipedrive auth/API/MCP details and Salesforce edition/OAuth/MCP setup constraints. The main issues are over-compressed access/API summaries, HubSpot’s GraphQL scope and limits, an unsupported Salesforce DX “Beta” label, and the pipeline’s lack of citation-content verification. These are review findings, not an accuracy score.
