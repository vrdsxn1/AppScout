# AppScout research instructions

Research one application at a time. Treat the app name and category from the
assignment list as input data; do not reinterpret them.

## Sources and claims

- Prefer official developer documentation, API references, authentication
  guides, pricing/access pages, and official MCP documentation.
- Tie each important claim to a specific source URL. Keep claims atomic so a
  reviewer can check which source supports which part.
- For every evidence record, set `field` to the single record field it
  supports. Split authentication, plans/pricing, limits, versions, MCP status,
  and tool-scope statements into separate claims when they have distinct facts
  or qualifications. Do not attach one source to an unrelated bundle of facts.
- Each evidence excerpt is extracted and quality-checked separately. A URL or
  successful retrieval is not proof. Claim support remains `unverified` until
  a reviewer judges it; never set it to supported from keyword overlap.
- A URL alone is not evidence that its attached claim is true. Inspect page
  content when possible. If the page cannot be retrieved, keep the claim
  `unverified` rather than assuming the URL supports it.
- If a source supports only part of a claim, narrow the claim to the supported
  part or mark the remaining part uncertain. Do not combine facts from several
  sources into one claim unless each part is clearly attributed.
- Do not infer labels such as Beta, GA, deprecated, preview, or generally
  available unless the source explicitly uses that label for the same feature.
- Do not infer API capabilities, auth methods, pricing, free access, or MCP
  availability from an app name, a search-result title, or general knowledge.
- Search-result snippets may help find sources, but do not treat a snippet as
  inspected page content.

## Preserve scope and uncertainty

- Preserve material edition, plan, subscription, scope/permission, API version,
  rate-limit, rollout, and feature limitations beside the claim they qualify.
- Keep plan, trial eligibility, regional availability, EAP/beta/GA status,
  read/write permissions, endpoint limits, and version qualifications in the
  exact atomic claim they qualify. If retrieved text only supports part, narrow
  the claim or leave it unverified.
- Distinguish a product's free tier or trial from API entitlement, paid API
  add-ons, and MCP tool availability. Do not assume one implies another.
- For APIs, say which surfaces and object/resource families are documented.
  Do not call an API broad or unrestricted without evidence; distinguish a
  limited GraphQL/CMS surface from a general REST API where relevant.
- Say an MCP exists only when a source confirms it. Distinguish native remote
  customer-data servers from local developer tooling and beta/preview products.
- Use `unknown` or `unclear` when evidence is missing, inaccessible, ambiguous,
  or too narrow to support a conclusion. Missing search results do not prove
  that an API or integration does not exist.
- Choose confidence based on the directness and completeness of retrieved
  evidence, not as an accuracy score. Do not present it as measured accuracy.

## Result fields

- Keep `description` to one line and factual.
- Describe `access_model` using evidence for self-serve, free/trial, paid,
  admin-approved, partnership/contact-sales gated, or `unknown` access.
- Use `REST`, `GraphQL`, `both`, or `unknown` for `api_type` only when the
  corresponding protocol is confirmed by the cited docs.
- Keep `api_breadth` concise and bounded; include relevant scope and limits.
- Use `build_now` only when evidence supports a usable API and practical
  access. Use `build_with_restrictions` for documented restrictions,
  `needs_outreach` only for a documented outreach gate, and `unclear` when the
  evidence does not settle the verdict.
- Keep `blockers` empty only when no blockers are documented; do not interpret
  that as proof that no access prerequisites exist.
- Return only the requested structured fields. The pipeline supplies the
  assignment app name, category, and check date.
