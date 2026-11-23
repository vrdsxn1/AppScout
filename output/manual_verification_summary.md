# Manual verification summary

## Scope

This is a **manually reviewed sample**, not an accuracy result for all 100 AppScout apps. The user reports opening each evidence link and checking the excerpt against the linked page. Only the exact 15 worksheet claim/app/URL matches were updated.

## Results

- Claims manually reviewed: 15
- Supported: 15
- Partially supported: 0
- Unsupported: 0
- Unavailable or unclear: 0

Apps reviewed: HubSpot, Pipedrive, Salesforce.

The automated `claim_supported` status was preserved for every record. Human verdicts are stored separately as `human_verdict`; `review_method` records that the user manually opened the links and checked the excerpts. No review date or reviewer notes were added.

No accuracy metric for the full research set is calculated from this sample.

## Exact records updated

| App | Field | Claim | Evidence URL |
| --- | --- | --- | --- |
| Salesforce | `auth_methods` | REST API clients must use an External Client App or Connected App with OAuth 2.0; creating new Connected Apps is restricted as of Spring '26 and Salesforce recommends External Client Apps. | https://developer.salesforce.com/docs/platform/api-rest/guide/intro-oauth-and-connected-apps.html |
| Salesforce | `api_type` | Salesforce REST API provides programmatic access to Salesforce data, and REST resources include records, collections, query results, metadata, and API information. | https://developer.salesforce.com/docs/platform/api-rest/guide/intro-rest.html |
| Salesforce | `access_model` | Sales Cloud uses a per-user, per-month subscription model and offers a free 30-day trial; the page states that API availability varies by edition/features. | https://www.salesforce.com/sales/pricing/ |
| Salesforce | `api_breadth` | API limits apply at the org level; the documented 24-hour allocation is 15,000 calls for Developer Edition, while Enterprise/Professional-with-API-access and Unlimited/Performance use license-based allocations. | https://developer.salesforce.com/docs/platform/salesforce-app-limits-cheatsheet/guide/salesforce-app-limits-platform-api.html |
| Salesforce | `mcp_status` | Hosted MCP Servers let compatible AI clients connect to a Salesforce org using standard OAuth-based authentication, with per-user OAuth 2.0 and PKCE documented for secure authentication. | https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/hosted-mcp-servers-overview.html |
| HubSpot | `auth_methods` | HubSpot's developer-platform authentication documentation says OAuth is required for multiple-account distribution, while static auth access tokens are used for a single account at a time. | https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/overview |
| HubSpot | `api_type` | HubSpot documents account service keys as scoped bearer credentials for direct REST API requests, and says users need the Developer tools access permission to create/manage them. | https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/account-service-keys |
| HubSpot | `api_breadth` | HubSpot states that new objects such as appointments, courses, listings, and services must be activated in the account before their records can be managed via API. | https://developers.hubspot.com/docs/api-reference/latest/crm/using-object-apis |
| HubSpot | `access_model` | HubSpot's CRM pricing page lists Free tools at $0/month, free for up to 2 users, with no credit card required. | https://www.hubspot.com/pricing/crm |
| HubSpot | `mcp_status` | The official MCP documentation lists read/write CRM records and activities, and states that MCP tool availability varies by HubSpot subscription, user permissions, and account configuration. | https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server |
| Pipedrive | `api_type` | The official API reference describes Pipedrive's API as RESTful, JSON-based, stateless, and validated against an API token; it links OpenAPI specifications for both v1 and v2. | https://developers.pipedrive.com/docs/api/v1 |
| Pipedrive | `auth_methods` | Pipedrive says OAuth 2.0 is necessary for apps available in its Marketplace and documents authorization-code and refresh-token flows using the oauth.pipedrive.com domain. | https://developers.pipedrive.com/docs/api/v1/Oauth |
| Pipedrive | `api_breadth` | Daily API token budgets are calculated as 30,000 base tokens multiplied by subscription-plan multiplier and seat count; the documented multipliers are Lite 1, Growth 2, Premium 5, and Ultimate 7. | https://pipedrive.readme.io/docs/core-api-concepts-rate-limiting |
| Pipedrive | `mcp_status` | Pipedrive states that its MCP is available to all customers on every plan, with usage subject to plan token limits and optional additional-token purchases. | https://www.pipedrive.com/en/features/mcp-server |
| Pipedrive | `access_model` | Pipedrive documents four subscription plans—Lite, Growth, Premium and Ultimate—and says API-token top-ups are available from the Growth plan. | https://support.pipedrive.com/en/article/how-does-pricing-work-in-pipedrive |
