# KEDDEH customer frontage: implementation and acceptance

This is the editable fourteen-route integration candidate for the existing KEDDEH Site `appgprj_6aa52748b7788191afe0f7f86fc78833`. Its existing audience and native project identity are retained in `frontage/route-manifest.json`. Git publication and the current cloud-host runtime are recorded separately from native Site publication. Native Site publishing is unavailable in this session; no public-site promotion is asserted.

## Working from the top down

1. Header and mobile navigation identify Platform, Architecture, Research, Evidence, Developers and Enterprise; nested research and product pages preserve the appropriate navigation context. Skip navigation moves keyboard focus to the main landmark. Escape closes the mobile menu and returns focus.
2. Each page presents a single H1 and a specific audience, problem, architectural fit, required inputs and proposed evaluation outcome. These business hooks are invitations to evaluate a bounded use case, not claims of market share, guaranteed savings or customer results.
3. The BRAINK, KEX and IL-LLM paths retain separate execution, routing and semantic responsibilities. Supporting VFS, observation and foundry paths point to current owner implementation and contracts.
4. Every authored section has an expandable source disclosure linking to a pinned owner source revision and the claim review. Page contracts bind customer interpretation to claim references and proposed acceptance checks. Source attribution is traceability; it does not convert a proposal into an independently assessed outcome.
5. Contextual evaluation calls to action lead to the existing interest page with a selected topic and originating path. Only nonpersonal topic/path information enters the query string. The browser uses textContent to present context, validates topic against existing options, and never prechecks consent or fills a purported customer statement.
6. Contact and interest forms label requirements, explain the handling purpose and expose enquiry privacy before submission. JavaScript records the enquiry through the same-origin API; a successful service response yields a durable registration reference. Without JavaScript, the form uses POST rather than placing personal details in a query string, and the page explains that the receipt journey needs JavaScript.
7. Service errors retain entered details, return focus to the status message, release the submit button and preserve the request identifier for retry. A request has a twenty-second client deadline. Owner review is the follow-up mechanism; this service does not send email, open customer accounts or subscribe newsletters.
8. Footer contact, privacy, evidence and developer links remain available on every page. Owner tokens, journals, agreement credentials and private customer records remain outside public assets.

## User functions and backend boundaries

| User function | Implementation | Behavior and fit |
|---|---|---|
| Navigate, return and skip | Static routes, semantic links, header landmarks, client.js | Browse the system, products and evidence with keyboard or pointer |
| Inspect section attribution | Native details/summary and pinned source links | Expand the section's source and interpret its claim scope |
| Inspect claims | `/api/claims`, four original scope records; twenty-two technical review entries | Dynamic source cards with a retained-review fallback |
| Read current runtime | `/api/runtime`, refresh button, live status region | Public sanitized family/healthy/boot readback; no owner credential |
| Describe a use case | Topic/context links, labeled form | Carry the evaluation subject into an explicit enquiry |
| Register interest | POST `/api/interest`, consent and request UUID | Private SQLite record and durable receipt; server validation and idempotency |
| Recover failed submission | Preserved fields and UUID, twenty-second deadline | Retry the same submission identity; no false success |
| Review consent/retention | `/privacy`, source-attributed version 1.0 | Enquiry handling and ninety-day maintenance policy |
| Obtain engine artifact | Existing public wheel link | Actual qualified 0.3.2 bytes; installation and operator authority remain separate |

The deployed frontage service is supplied by the qualified owner controller image and existing family launcher. Browser requests remain same-origin. The service enforces payload bounds, field validation, origin checks, explicit consent, idempotent receipt identity, a private durable store and retention maintenance. Browser failure tests inject controlled responses; they do not stop shared owner services or establish real WAN availability. The server implementation is pinned in each applicable source disclosure.

## Evidence and attribution contracts

- `frontage/page-contracts.json`: audience, fit, inputs, expected evaluation, topic, source revision and claim references for every route.
- `frontage/copy-and-clickable-inventory.json`: rendered customer copy, every link, summary, button and form control, with source context and stable route/index locator. Header/footer items are interaction contracts rather than technical assertions.
- `frontage/claims.json`: four original dynamic evidence assertions.
- `frontage/claim-review.json`: twenty-two explicitly qualified technical assertions and the derivation needed for stronger interpretations.
- `docs/frontage/DOM_EVIDENCE.json`: tested execution scope, counts and controlled-failure results.
- `docs/frontage/CUSTOMER_DOM_INVENTORY.json`: actual Chromium-rendered inventory including dynamically loaded claims.
- `docs/frontage/PAGE_REVIEW.md`: route-by-route content, relevance and customer journey review.

Owner attribution remains KEDDEH Systems for supplied concepts, technology and runtimes. Integration, UX and test changes are attributable through Git authorship and revision. No contributor assignment, licence or independent assessment is invented. Existing qualified executable hashes and image admission remain unchanged by static frontage edits.

## HCI basis and limits

The implementation targets explicit named landmarks, single page H1, linked labels, visible keyboard focus, native disclosures, preserved navigation context, mobile layout, clear consent, recoverable errors and live status announcements. These correspond to relevant WCAG 2.2 considerations including 1.3.1, 2.1.1, 2.4.1, 2.4.7, 3.3.1, 3.3.2 and 4.1.3. Reference: https://www.w3.org/TR/WCAG22/ . A direct retrieval returned HTTP 403 in this environment; no retained current standards download is claimed. This scoped DOM suite is not a full WCAG conformance assessment: screen-reader, manual visual contrast, browser/assistive-technology matrix and independent accessibility review remain promotion tasks.

## Development and verification

Run `python scripts/develop_frontage.py` from this repository to regenerate page contracts, evaluation panels and section disclosures while retaining the existing Site binding. Run `node --check frontage/client.js`. Run `node scripts/test_customer_frontage.mjs --container-no-sandbox` from the canonical namespace repository against the actual owner-supervised candidate. The no-sandbox flag is limited to this isolated container Chromium test.

After static source changes, restart only the owner-labeled keddeh.com resident controller so its source binding includes the updated frontage; retain private state, agreement, tokens and VFS cursors. Obtain actual boot and healthy-workstation readback before recording deployment success. Native Site promotion requires its existing source/publish/readback capability and is tracked separately.
