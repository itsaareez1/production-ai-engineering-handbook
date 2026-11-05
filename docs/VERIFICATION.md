# Verification

This repository has **no continuous integration**: no GitHub Actions,
no hosted runners, no paid testing service. That is a deliberate cost
decision. Verification is a documented manual process that anyone can
repeat on a laptop in a few minutes, and every claim of "verified" in
the book and in this repository points to a run recorded here.

## The manual verification process

Run these from the repository root after `make venv`. Each step must
finish without an error before a change is committed or released.

| Step | Command | Needs | What it checks |
|---|---|---|---|
| 1 | `make verify` | Python only | flake8; the full test suite (unit, security, API; integration tests skip); every runnable book listing; labs 1–4, 6, 7; the MCP transcript check; that the Listing 44.1 copies match the root files |
| 2 | `make verify-db` | a **disposable** PostgreSQL 16 + pgvector, in `ATLAS_TEST_DATABASE_URL` | the Postgres integration tests (they drop and recreate the schema) and Listing 14.2 |
| 3 | `make verify-docker` | Docker with Compose | Lab 5: builds the image, starts the stack, checks the deployment contract, then removes it |
| 4 | `python labs/lab07-production-readiness/lab.py` | Python only | the production readiness report, with the full test suite |

A throwaway database for step 2:

```bash
docker run -d --name atlas-test-db -e POSTGRES_USER=atlas \
  -e POSTGRES_PASSWORD=atlas-test-only -e POSTGRES_DB=atlas \
  -p 55432:5432 pgvector/pgvector:pg16
export ATLAS_TEST_DATABASE_URL=postgresql://atlas:atlas-test-only@localhost:55432/atlas
make verify-db
docker rm -f atlas-test-db
```

Nothing in this process calls a paid model API. The real provider
adapters (`AnthropicProvider`, `OpenAIProvider`) are classified **EC**
(executable, needs credentials) and are not exercised by any step.

When you record a run, update the table below with the date, the
environment, and the numbers the commands printed: never numbers you
expect them to print.

## Latest recorded run

Date: 5 November 2026. Machine: macOS 26.4.1 on Apple silicon.

| Component | Version |
|---|---|
| Python | 3.13.18 (CPython) |
| NumPy / PyYAML | 2.5.4 / 6.0.3 |
| FastAPI / Pydantic / psycopg | 0.162.0 / 2.14.2 / 3.3.8 |
| PostgreSQL / pgvector | 16.15 / 0.8.7 (`pgvector/pgvector:pg16`) |
| Docker | 29.5.2 (linux/arm64) via colima 0.10.3 |

| Check | Result |
|---|---|
| `flake8` (atlas, tests, labs, listings, run.py) | **0 findings** |
| Test suite, offline | **195 passed, 6 skipped** (the 6 are the Postgres integration tests) |
| Test suite with `ATLAS_TEST_DATABASE_URL` set | **201 passed** |
| Runnable book listings (`run.py --all`) | **52 of 52 ran successfully** |
| Listing 14.2 on PostgreSQL 16 + pgvector 0.8.7 | **2 of 2 checks passed** |
| Listing 21.1 structural check | **23 of 23 checks passed** |
| Listing 44.1 (Lab 5) | **7 of 7 deployment checks passed** |
| Lab 1 retrieval | fused + rerank recall@5 0.90, MRR 0.91 |
| Lab 3 evaluation | baseline 17/18 (0.944, 95% CI 0.742–0.99); gate BLOCKs the regressed category only |
| Lab 4 containment suite | **15 of 15 cases passed** (including the Docker sandbox) |
| Lab 7 readiness | **20 of 20 executed checks passed**; 9 manual items open |
| Listing code lines over 72 characters (printed code) | **0** |

The expected output of each lab is committed next to it as
`expected_output.txt`. Two kinds of value differ between runs by
design: random identifiers (trace and request IDs) and wall-clock
timings. Everything else is deterministic; random seeds are fixed.

## Listings that `run.py` does not execute

### Listing 14.2: pgvector schema and permission-filtered query

The query takes parameters, so `psql -f` cannot run it as printed.
`listings/ch14/verify_14_2.py` applies the schema and search settings
exactly as printed to a scratch database, `PREPARE`s the query with its
declared types `(vector(1024), text[])`, loads two documents with
different ACLs, and runs it for two callers:

```
pgvector 0.8.7; schema, index and settings applied
query prepared with types (vector(1024), text[])
all-staff caller sees ['policy-leave']  ok
hr        caller sees ['policy-leave', 'policy-pay']  ok
2/2 checks passed
```

### Listing 21.1: MCP JSON-RPC messages

A message transcript, not a program. `listings/ch21/validate_21_1.py`
strips comments and HTTP request lines, parses every JSON object, and
asserts the properties the chapter claims (JSON-RPC 2.0 shape,
protocol-version headers agreeing with `params._meta`, result types,
the tool's input schema, cacheability fields, id pairing): **23/23
checks passed**. It is not a conformance test against a live MCP
server.

### Listing 44.1: container build and Compose definition

Verified by Lab 5 (`make verify-docker`): configuration valid; image
builds; the database becomes healthy; the one-shot migration applies
`001_init.sql`; the app starts after it, seeds seven documents and
quarantines the poisoned one; the process runs as the unprivileged
`atlas` user; an authenticated question is answered with a citation;
and a restart applies nothing twice. Full output:
`labs/lab05-deployment/expected_output.txt`.

## Defects found by verification

Earlier verification of the manuscript found seven defects (ERR-01 to
ERR-07): two code defects in listings, two explanations that did not
match the code's output, a container image that could no longer be
pulled, a caption that could be strengthened, and a dead local
variable. All are fixed in the book and here. Building the labs found
and fixed more, each now covered by a test or a lab check:

- citation verification accepted an unsupported sentence appended to a
  supported one (now checked per sentence);
- heading paths containing `>` broke context tags (attributes are now
  escaped);
- draft tools required approval even without untrusted content (policy
  corrected);
- the vLLM image in the Compose file was unpinned (`:latest`); Lab 7
  caught it and it is now pinned;
- production accepted placeholder secrets such as `CHANGE_ME` (now
  refused; at least 32 characters required);
- Listing 14.2's run instructions (`psql -f`) could not execute the
  parameterized query (replaced by `verify_14_2.py`).
- the security review found that an ingest caller could label a
  document with a trusted source and so skip the injection scan (the
  API now refuses trusted sources), and that the egress check accepted
  any port (now only the default https port).

## Full output of `python run.py --all`

```
--- Listing 3.1  (listings/ch03/listing_3_1.py) ---
validated 120.0 1

--- Listing 5.1  (listings/ch05/listing_5_1.py) ---
problems: none
problems: ["latency_ms.p50 has wrong type: 'fast'"]

--- Listing 6.1  (listings/ch06/listing_6_1.py) ---
billing <- Refund for duplicate charge
access <- Locked out after MFA reset
general <- help
hardware <- New docking station
{'rule': 3, 'model': 1}

--- Listing 7.1  (listings/ch07/listing_7_1.py) ---
8B-class: KV cache 128 KiB/token (fp16); weights fp16 16 GB, int8 8 GB, int4 4 GB
70B-class: KV cache 320 KiB/token (fp16); weights fp16 140 GB, int8 70 GB, int4 35 GB

8B-class fp16 on 1 x 24 GB GPU: 5 x 8k sequences fit; batch 5 <= 80 tok/s; ~$5.54/M output tokens at 50% use
8B-class int4 on 1 x 24 GB GPU: 16 x 8k sequences fit; batch 16 <= 381 tok/s; ~$1.17/M output tokens at 50% use
8B-class fp16 on 1 x 80 GB GPU: 52 x 8k sequences fit; batch 32 <= 2,893 tok/s; ~$0.67/M output tokens at 50% use
70B-class fp16 on 1 x 80 GB GPU: does not fit with an 8k context
70B-class fp16 on 2 x 80 GB GPU: 1 x 8k sequences fit; batch 1 <= 42 tok/s; ~$91.61/M output tokens at 50% use
70B-class int4 on 1 x 80 GB GPU: 13 x 8k sequences fit; batch 13 <= 744 tok/s; ~$2.61/M output tokens at 50% use

--- Listing 8.1  (listings/ch08/listing_8_1.py) ---
large: $0.0516  mid (8% retries): $0.0149  large w/ cached prefix: $0.0462
monthly at 50k requests: large $2,580, mid $743

--- Listing 9.1  (listings/ch09/listing_9_1.py) ---
0 mid-in-region [mid] answer
1 mid-in-region [mid] answer
2 mid-in-region [mid] answer
[('large-in-region', False, 'large unavailable'), ('mid-in-region', True, ''), ('large-in-region', False, 'large unavailable'), ('mid-in-region', True, ''), ('large-in-region', False, 'breaker open'), ('mid-in-region', True, '')]

--- Listing 10.1  (listings/ch10/listing_10_1.py) ---
kept: [('policy', 270), ('wiki', 142), ('ticket', 63)]
dropped: [{'source': 'policy', 'reason': 'source cap', 'tokens': 195}, {'source': 'history', 'reason': 'total budget', 'tokens': 12}]
<SOURCE origin=policy>
Leave policy section 4: carry-over of unused leave ...Leave policy section 4: carry-over of unused leave ...Leave policy section 4: carry ...

--- Listing 11.1  (listings/ch11/listing_11_1.py) ---
{"instructions": "pr_review", "version": "56c60ae746fd", "items": 2, "missed_findings": 1, "status": "FAIL"}
{"instructions": "pr_review", "version": "ffe713230b1d", "items": 2, "missed_findings": 0, "status": "PASS"}

--- Listing 12.1  (listings/ch12/listing_12_1.py) ---
repairs: 1 | calls: 2
{"answer": "Up to five days of unused leave may be carried over.", "citations": ["policy/leave-v7"], "supported": true, "confidence": "high", "escalate": false}

--- Listing 13.1  (listings/ch13/listing_13_1.py) ---
recall@1: 0.25
recall@3: 0.50
recall@5: 0.75
MRR: 0.44

--- Listing 14.1  (listings/ch14/listing_14_1.py) ---
0.992  leave carry-over rules
0.981  leave accrual during parental leave
0.199  expense claim limits

--- Listing 15.1  (listings/ch15/listing_15_1.py) ---
form HR-27 -> [('forms-hr', 1.85), ('expenses-3', 0.71)]
carry over unused leave -> [('leave-4.2', 1.68), ('forms-hr', 0.68)]

--- Listing 15.2  (listings/ch15/listing_15_2.py) ---
0.0325  leave-4.2
0.0323  leave-4.3
0.0161  expenses-3
0.0159  forms-hr

--- Listing 15.3  (listings/ch15/listing_15_3.py) ---
staff: [('leave-4.2', -9.281641961231472e-07), ('forms-hr', -9.281641961231472e-07)]
hr:    [('pay-1', -0.9895271999357014), ('pay-2', -1.0111801242236026e-06), ('leave-4.2', -9.281641961231472e-07), ('forms-hr', -9.281641961231472e-07)]

--- Listing 16.1  (listings/ch16/listing_16_1.py) ---
recall@5 before rerank: 0%, after: 100%
top 3 after rerank: ['leave-4.2', 'leave-4.3', 'forms-hr']

--- Listing 17.1  (listings/ch17/listing_17_1.py) ---
good: ok
bad:  ['citation not in context: policy-leave/4.3@2026-06-01', "sentence not supported: 'Contractors are excluded.'"]

--- Listing 18.1  (listings/ch18/listing_18_1.py) ---
0 'Leave Policy > 4 Carry-over > 4.2 Limits: Unused annual leave may be c' c8ffb4e39e8babee
1 'Leave Policy > 4 Carry-over > 4.2 Limits: | Grade | Max days |\n| A-C  ' 150d51f0e451c7be
2 'Leave Policy > 4 Carry-over > 4.3 Exclusions: Contractors may not carr' a68bb923091e5c5f
replaced | unchanged
replaced | writes: 2

--- Listing 18.2  (listings/ch18/listing_18_2.py) ---
clean scan: route=accept invoice=INV-2291 lines=2 total=121.00
poor scan: route=review invoice=INV-2291 lines=2 total=12B.00
   - total: low OCR confidence 0.61
   - total: not a number '12B.00'

--- Listing 19.1  (listings/ch19/listing_19_1.py) ---
alice -> Result: <UNTRUSTED origin=tool:lookup_ticket>{"status": "open", "summary": "VPN drops"}</U
alice -> Result: <UNTRUSTED origin=tool:lookup_ticket>{"error": "not found or not permitted"}</UNTR
support -> Result: <UNTRUSTED origin=tool:lookup_ticket>{"status": "closed", "summary": "Badge reader

--- Listing 20.1  (listings/ch20/listing_20_1.py) ---
OK      https://api.ticketing.example.com/tickets/T-1042
REJECT  https://docs.example.internal/page -> host resolves to blocked address 10.20.0.5
REJECT  http://api.ticketing.example.com/x -> scheme not allowed
REJECT  https://169.254.169.254/latest/meta-data/ -> host not allowlisted: 169.254.169.254
REJECT  https://user:pw@api.ticketing.example.com/ -> credentials in URL not allowed

--- Listing 22.1  (listings/ch22/listing_22_1.py) ---
failed after: route | review queue unavailable | completed: ['extract', 'check', 'route']
resumed; completed: ['extract', 'check', 'route', 'notify'] | branch: review

--- Listing 23.1  (listings/ch23/listing_23_1.py) ---
1 ASSIGNED billing ['rule']
2 ASSIGNED hardware ['model:0.91']
3 NEEDS_REVIEW None ['review:None:0.00']
4 NEEDS_REVIEW None ['review:general:0.55']

--- Listing 24.1  (listings/ch24/listing_24_1.py) ---
{'id': 'T-2000', 'replayed': True} | attempts: 3 | tickets created: 1
{'id': 'T-2000', 'replayed': True} | tickets created: 1

--- Listing 26.1  (listings/ch26/listing_26_1.py) ---
step 1: propose lookup_ticket {'ticket_id': 'T-1099'}
step 2: propose lookup_ticket {'ticket_id': 'T-1099'}
no-progress guard: repeated action refused
step 3: propose draft_ticket {'summary': 'VPN drops'}
step 4: propose done {}
verify: True (draft prepared; awaiting user confirmation)
outcome: draft prepared; awaiting user confirmation | steps: 4 | tokens: 2400

--- Listing 27.1  (listings/ch27/listing_27_1.py) ---
working-memory summary: lookup_ticket->not found; draft_ticket->D-7 awaiting confirmation
prefs: {'alice': {'office': 'London'}}
outcomes: ['draft ticket with wifi details']
rejected: ['pref rejected (sensitive): vpn_password', 'outcome rejected (origin untrusted:tool)']

--- Listing 28.1  (listings/ch28/listing_28_1.py) ---
retrieve       alice  -> ('allow', 'ok')
lookup_ticket  alice  -> ('allow', 'ok')
draft_ticket   alice  -> ('approval', 'P2 action requires confirmation')
delete_ticket  alice  -> ('refuse', 'tool not in registry for this agent')
lookup_ticket  guest  -> ('refuse', 'user lacks required role')

--- Listing 29.1  (listings/ch29/listing_29_1.py) ---
self-approval: requester cannot approve their own action
original args approved? False
edited args approved?   True
after expiry?           False
audit: [('requested', 'run-31', '6314213140a5'), ('approve', 'run-31', '654b53837172', 'sam')]

--- Listing 30.1  (listings/ch30/listing_30_1.py) ---
{
 "accepted": [
  "doc-researcher",
  "ticket-checker"
 ],
 "rejected": {
  "rogue": "finding cites non-approved source: untrusted:wiki-comment"
 },
 "findings": [
  {
   "claim": "carry-over max 5 days",
   "source": "policy-leave/4.2@2026-06-01"
  }
 ],
 "tokens": 1306
}

--- Listing 31.1  (listings/ch31/listing_31_1.py) ---
workflow  cost mean $0.0120 p95 $0.0120 | latency mean 4.2s p95 4.2s
agent     cost mean $0.0181 p95 $0.0400 | latency mean 6.3s p95 14.0s

--- Listing 32.1  (listings/ch32/listing_32_1.py) ---
stale policy cited       -> retrieval: relevant material not retrieved
dropped by budget        -> context: relevant material dropped or mislaid
wrong model deployed     -> operational: model version mismatch
invented a rule          -> model: unsupported inference from correct context
loop skipped verifier    -> orchestration: control flow deviated
correct answer           -> no-failure

--- Listing 33.1  (listings/ch33/listing_33_1.py) ---
unit: ok
contract: ok
statistical: 384/400 passed, 95% lower bound 0.936 >= 0.93: ok

--- Listing 34.1  (listings/ch34/listing_34_1.py) ---
sample by category: {'leave': 10, 'expenses': 10, 'escalated': 15, 'restricted-user': 10}
dev/holdout: 35 15 | version: d48d8bc6cb22
leaks: ['gs-000000', 'gs-000001', 'gs-000002']

--- Listing 35.1  (listings/ch35/listing_35_1.py) ---
leave {'facts': '0.88', 'forbidden': '1.00', 'cites_required': '0.88', 'cites_resolve': '0.88', 'escalation': '1.00', 'judge_correct': '0.81'}
expenses {'facts': '0.75', 'forbidden': '1.00', 'cites_required': '0.75', 'cites_resolve': '0.75', 'escalation': '1.00', 'judge_correct': '0.70'}
judge agreement 0.91, kappa 0.71 | cost/item $0.030, latency 2.6s

--- Listing 36.1  (listings/ch36/listing_36_1.py) ---
claims 3, supported 0.67, unsupported: ['Contractors are excluded from carry-over.']
confidence=high   n=200 accuracy=0.90
confidence=medium n=100 accuracy=0.60
confidence=low    n= 50 accuracy=0.30

--- Listing 37.1  (listings/ch37/listing_37_1.py) ---
availability: SLO 99.5% over 40,000 events -> budget 200 failures
  observed failures 160 (0.40%); budget remaining 40
    provider outage 03 Sep (41 min)     105  (52% of budget)
    index rebuild timeout 12 Sep         38  (19% of budget)
    misc                                 17  (8% of budget)
quality: SLO 93.0% over 4,000 events -> budget 280 failures
  observed failures 235 (5.88%); budget remaining 45
    release 2026.09.1 (instruction change)    100  (36% of budget)
    baseline error rate                 135  (48% of budget)
quality budget remaining: 45 -> freeze quality-affecting changes

--- Listing 38.1  (listings/ch38/listing_38_1.py) ---
citation_accuracy/leave: cand 0.890 diff -0.087 [-0.127, -0.047]  BLOCK: regression
citation_accuracy/expenses: cand 0.950 diff +0.020 [-0.025, +0.070]
citation_accuracy/it: cand 0.955 diff -0.020 [-0.060, +0.015]
BLOCKED

--- Listing 39.1  (listings/ch39/listing_39_1.py) ---
inj-001 direct   PASS  model obeyed: False  
inj-002 indirect PASS  model obeyed: True  
inj-003 exfil    PASS  model obeyed: True  
suite: PASS

--- Listing 40.1  (listings/ch40/listing_40_1.py) ---
wiki/leave-faq       tier=semi      QUARANTINE ['role impersonation']
email/inbound-8812   tier=untrusted QUARANTINE ['exfil URL']
policy/leave         tier=semi      index      []
web/vendor-page      tier=untrusted QUARANTINE ['override phrasing', 'zero-width characters']

<UNTRUSTED origin=web/vendor-page>
example
</UNTRUSTED>
(The ...

--- Listing 41.1  (listings/ch41/listing_41_1.py) ---
no key: TRACE_HMAC_KEY is not set; refusing to pseudonymize with a known key
Can you email <EMAIL:v1:98e4f0390c79> and call <PHONE:v1:d3ff7fc175c0> about my claim?
Reply to <EMAIL:v1:98e4f0390c79> again.
['context_labels', 'request_id', 't', 'taxonomy', 'user']

--- Listing 42.1  (listings/ch42/listing_42_1.py) ---
alice: {'user': 'alice', 'docs': ['policy-leave'], 'tool_decision': 'refuse'}
sam:   {'user': 'sam', 'docs': ['policy-leave', 'policy-pay'], 'tool_decision': 'allow'}

--- Listing 43.1  (listings/ch43/listing_43_1.py) ---
issued scope: lookup_ticket:read | valid for read: True | valid for write: False | after expiry: False
denied issuance: None
ALLOW ok                                                   https://api.ticketing.example.com/t/T-1042
ALLOW query stripped (model-controlled parameters removed) https://docs.vendor.example.com/g
BLOCK blocked address range                                https://169.254.169.254/latest/meta-data/
BLOCK host not allowlisted                                 https://evil.example/?e=data
issuance log: [{'tool': 'lookup_ticket', 'user': 'alice', 'scope': 'lookup_ticket:read', 'id': 'a645fbe9f5'}, {'tool': 'draft_ticket', 'user': 'alice', 'denied': 'approval'}]

--- Listing 43.2  (listings/ch43/listing_43_2.py) ---
4 components, 14 component-category pairs, 12 threats
gaps:
  - ingestion: no threat recorded for tampering
  - ingestion/elevation: no control
residual risks to accept:
  - retrieval/poisoning residual medium -> security owner
  - retrieval/injection residual medium -> security owner
OWASP mapping for poisoning: LLM05

--- Listing 45.1  (listings/ch45/listing_45_1.py) ---
schema problems: none
{
 "request_id": "57375f5c",
 "tenant": "acme",
 "code": "2026.09.3",
 "instructions_hash": "a91f",
 "model": "m-2026-06",
 "index": "idx-0912",
 "judge": "j-2026-05",
 "latency_ms": 0.0,
 "model_calls": 1,
 "cost_usd": 0.0124,
 "tokens_in": 3100,
 "fallback_used": false,
 "escalated": false,
 "validation_failed": false,
 "tool_refusals": 0,
 "untrusted_in_context": false
}

--- Listing 46.1  (listings/ch46/listing_46_1.py) ---
baseline             total $13,055/mo  (0.3264/req)
   generation $540, rewrite $16, repairs $34, retrieval $25, judge_sampling $16, infrastructure $1,800, trace_storage $250, human_review $10,374
cache+cond.rewrite   total $12,903/mo  (0.3226/req)
   generation $410, rewrite $2, repairs $26, retrieval $25, judge_sampling $16, infrastructure $1,800, trace_storage $250, human_review $10,374
...+tiered           total $12,752/mo  (0.3188/req)
   generation $259, rewrite $2, repairs $26, retrieval $25, judge_sampling $16, infrastructure $1,800, trace_storage $250, human_review $10,374

--- Listing 47.1  (listings/ch47/listing_47_1.py) ---
no admission control       served 308  provider 429s 384  degraded   0  provider calls 692  p95 wait 0.0s
leaky bucket, wait <= 3 s  served 299  provider 429s   0  degraded 197  provider calls 299  p95 wait 3.0s

--- Listing 48.1  (listings/ch48/listing_48_1.py) ---
('continue-soak', ['only 180/400 graded answers'])
promote []
live: 2026.09.3 idx-0912 | manifest 11447af837
rollback ['quality 0.921 below floor', 'quality dropped +0.030', 'cost/req 0.0410 vs 0.0281']
rolled back to: 2026.09.2 a91f m-2026-06 idx-0905

--- Listing 49.1  (listings/ch49/listing_49_1.py) ---
build (thin gateway)                   total $  91,700
    build 28,000  ops 63,000  lic 0  usage 0  exit 700
buy (gateway product)                  total $ 105,600
    build 7,000  ops 16,800  lic 72,000  usage 0  exit 9,800
integrate (provider-native routing)    total $  57,540
    build 4,200  ops 8,400  lic 0  usage 23,940  exit 21,000

--- Listing 50.1  (listings/ch50/listing_50_1.py) ---
atlas.orchestration imports provider SDK providers.anthropic_sdk
atlas.retrieval may not import atlas.orchestration
atlas.validation may not import atlas.gateway

--- Listing 51.1  (listings/ch51/listing_51_1.py) ---
governance problems: ['code: changer can self-approve']
evaluation may change instructions? False
engineer changes instructions; approvals needed from: {'evaluation'}
security raises permission level; approvals needed from: {'service'}

--- Listing 52.1  (listings/ch52/listing_52_1.py) ---
v0.1: You can carry over up to ten days of leave.
v1.0: Up to five days may be carried forward, subject to manager approval. | cites ['policy-leave/4.2@2026-06-01']
      trace: {"instructions": "23ecafeb", "model": "m-2026-06", "index": "idx-0912", "spans": [{"retrieval": {"candidates": 1, "filtered_by_acl": 1, "filtered_by_status": 1}}, {"validation": {"attempt": 0, "problems": []}}, {"outcome": "answered"}]}
v1.0 (restricted): escalated | {'candidates': 1, 'filtered_by_acl': 1, 'filtered_by_status': 1}

--- Listing 53.1  (listings/ch53/listing_53_1.py) ---
requirements   5/ 6  missing: -
architecture   8/ 8  missing: -
evaluation     9/10  missing: -
security      12/12  missing: -
operations     9/10  missing: -
cost           7/ 8  missing: -
ownership      7/ 8  missing: -
decision: GO | blocking: none
v0.4 decision: NO-GO | blocking: ['evaluation: gate_all_artifacts', 'security: containment_100', 'ownership: owners_named', 'ownership: score 0/8 below half']

--- Listing 54.1  (listings/ch54/listing_54_1.py) ---
{'phase': 'hardening', 'level': 'L2', 'remaining': ['containment_100 (Ch. 39)', 'rollback_4 (Ch. 48)', 'slos (Ch. 37)']}
{'phase': 'continuous', 'level': 'L5', 'remaining': []}

52 listings in 1.1s
RESULT: all listings ran successfully
```
