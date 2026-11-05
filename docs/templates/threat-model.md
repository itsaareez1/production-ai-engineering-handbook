# Threat model: <system name>

Template from Appendix C.5 of *The Production AI Engineering Handbook*
(Chapter 43). Copy this file, fill every section, and keep it in the
repository next to the code. Update it at every architecture change,
new tool, new data source, or new trust tier. The rows in *italics*
are worked examples from Atlas; replace them.

Listing 43.2 (`listings/ch43/listing_43_2.py`) keeps the same model as
data and checks it mechanically; use whichever form your team reviews.

## 1. Scope and version

| Field | Value |
|---|---|
| System | |
| Architecture version | |
| Date | |
| Authors | |
| Reviewer | |

## 2. Assets

| Asset | Why it matters | Classification |
|---|---|---|
| *Restricted documents (salary bands, credentials)* | *disclosure harms employees and security* | *restricted* |
| *Ability to create tickets (tools)* | *actions on behalf of users* | *internal* |
| *Daily model budget* | *unbounded consumption* | *internal* |

## 3. Components and trust zones

| Component | Zone | Runs as (identity) |
|---|---|---|
| *API (`atlas/api`)* | *application* | *service account; caller identity from a signed token* |
| *Ingestion* | *application* | *ingest role* |
| *Model gateway* | *application to provider* | *service account* |

## 4. Data flows and trust boundaries

| Flow | From → To | Crosses boundary? | Data |
|---|---|---|---|
| *Question* | *user → API* | *yes* | *question text, token* |
| *Document* | *wiki/web → ingestion* | *yes (untrusted)* | *document body* |
| *Prompt* | *gateway → provider* | *yes (third party)* | *context, may be restricted* |

## 5. Threats

For each component: spoofing, tampering, repudiation, information
disclosure, denial of service, elevation of privilege; for components
that handle model input or output, also injection, excessive agency,
data and model poisoning, and unbounded consumption. Record an attack
path, or "not applicable" with a reason.

| ID | Component | Category | Description and attack path |
|---|---|---|---|
| *T1* | *Ingestion* | *Injection (indirect)* | *a wiki page addresses the assistant and asks it to fetch payroll* |
| *T2* | *API* | *Spoofing* | *caller claims another identity in the request body* |
| *T3* | *Gateway* | *Unbounded consumption* | *a loop or abuse exhausts the budget* |

## 6. Controls

| Threat | Control | Chapter | Status (in place / planned / missing) |
|---|---|---|---|
| *T1* | *scan at ingestion and quarantine; untrusted tags in context; approval for side effects* | *40, 43* | *in place* |
| *T2* | *identity only from the signed token; body claims ignored* | *42* | *in place* |
| *T3* | *daily cost cap, agent step budget* | *46, 26* | *in place* |

## 7. Residual risk

Injection through untrusted content is never recorded as "none".

| Threat | Residual risk (low / medium / high) | Accepted by | Date |
|---|---|---|---|
| *T1* | *medium* | | |

## 8. Tests

A threat with no test is a threat whose control is assumed.

| Threat | Test |
|---|---|
| *T1* | *`tests/security/test_security.py::test_poisoned_document_posted_via_api_is_quarantined`* |
| *T2* | *`tests/security/test_security.py::test_identity_claims_in_the_body_are_ignored`* |
| *T3* | *`tests/unit/test_gateway_and_service.py::test_daily_cost_cap_stops_calls`* |

## 9. Open actions

These block the readiness review (Chapter 53) where they touch a
mandatory item.

| Action | Owner | Due |
|---|---|---|
| | | |
