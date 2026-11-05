# Lab 4: Secure an AI agent

Book chapters: 19, 26–29, 39–43. Estimated time: 45–60 minutes.

## Objectives

- Authorize every tool call with the caller's identity, not the model's claims
- Test prompt injection by its effect, not by whether the model obeyed
- Require approval for side-effecting tools when untrusted content is in the turn
- Stop a looping planner with a step budget and a no-progress guard
- Bind approvals to the exact proposal and keep a tamper-evident audit trail
- Run untrusted code in a sandbox with no network

## Prerequisites

- Python 3.12 or later and the repository's virtual environment (`make venv`)
- No API key, no network access to model providers, no paid service
- Docker (optional): step 8 runs only if `docker` is available; without it that case is reported as skipped

## Estimated time

45–60 minutes.

## Architecture

```text
user ─► TicketAgent: planner (model) ─► decide(identity, tool, level, untrusted) ─► allow | approval | refuse
                         │                                    │
                         ▼                                    ▼
                  Tool(args, identity)               Approvals (hash-bound, TTL, no self-approval)
                         │
                         ▼
                  MemoryAudit (hash chain)        sandbox: docker run --network none --read-only ...
```

## Files

| File | Purpose |
|---|---|
| [`lab.py`](lab.py) | the whole lab |
| [`expected_output.txt`](expected_output.txt) | output of a verified run |
| [`../../atlas/agents/agent.py`](../../atlas/agents/agent.py) | tools, policy, approvals, the bounded agent |
| [`../../atlas/agents/records.py`](../../atlas/agents/records.py) | idempotent records and the hash-chained audit log |
| [`../../atlas/security/controls.py`](../../atlas/security/controls.py) | injection scanner, redaction, egress checks |

## Steps

1. **Tools and levels.** Lookup is P1 (read), draft is P2 (reversible write).
2. **Authorization.** A forbidden ticket and a missing one return the same message, so the tool leaks nothing.
3. **Injection tests.** Claimed identities in the body are ignored; override requests cannot reach restricted documents; poisoned documents are quarantined at ingestion and via the API.
4. **Untrusted-content rule.** A draft prompted by untrusted content waits for a person.
5. **Budget and no-progress.** A planner that repeats itself is refused without a tool call and stopped by the step budget.
6. **Approval.** The requester cannot approve; a reviewer's edit binds the approval to the edited arguments only.
7. **Audit.** The hash chain verifies, and tampering with one entry is detected.
8. **Sandbox.** Untrusted code runs as nobody, read-only, with no capabilities and no network.

## Complete code

The complete, runnable code for this lab is [`lab.py`](lab.py) (115 lines), which uses the `atlas` package in this repository. Read it top to bottom: each step above is one block, headed by a `print("== Step N ...")` line.

## Commands

From the repository root:

```bash
make venv            # once
python labs/lab04-agent-security/lab.py
```

## Expected output

Captured from a verified run (macOS, Python 3.13) on 5 November 2026 and committed as [`expected_output.txt`](expected_output.txt).

```text
== Step 1: tool definitions and levels
  lookup_ticket  P1  Return status and subject of a support ticket by its identif...
  draft_ticket   P2  Prepare a new support ticket draft for the user to confirm. ...

== Step 2: authorization runs with the caller's identity
  [PASS] alice cannot read bob's ticket; same message as a missing one: {'ok': False, 'error': 'not found or not permitted'}
  [PASS] support can read it

== Step 3: prompt-injection and identity-claim tests (effects)
  [PASS] identity claimed in the body is ignored: escalated
  [PASS] override request cannot reach a restricted document: escalated
  [PASS] poisoned wiki page was quarantined at ingestion: ['assistant-directed note', 'tool or retrieval coercion']
  [PASS] injected document posted through the API is quarantined: ['override phrasing', 'role impersonation']

== Step 4: the untrusted-content rule for draft tools
  [PASS] draft with untrusted content in the turn needs approval: draft tool with untrusted content in the turn
  [PASS] agent pauses for approval instead of drafting: approval_id=A-9124acd4

== Step 5: execution budget and no-progress guard
  [PASS] stubborn planner is stopped by the budget: 4 steps, 3 repeats refused without a tool call

== Step 6: human approval
  [PASS] requester cannot approve (not a reviewer)
  [PASS] reviewer approves an edited proposal
  [PASS] approval binds to the edited arguments only

== Step 7: audit trail
  7 audit entries, last: approval.decided by rita
  [PASS] hash chain verifies
  [PASS] tampering is detected

== Step 8: sandbox for code execution (Docker)
  docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 0.5 --user 65534:65534 python:3.12-slim python -c '<untrusted code>'
  [PASS] sandboxed code has no network: OSError: [Errno 101] Network is unreachable

Containment suite: 15/15 cases passed
```

## Verification

The lab worked if:

- The last line reads `Containment suite: 15/15 cases passed` (14/14 plus a skip without Docker)

## Common errors

| Symptom | Fix |
|---|---|
| Step 8 fails with `Cannot connect to the Docker daemon` | Start Docker (Docker Desktop, or `colima start`), or accept the skip. |
| First run of step 8 is slow | Docker pulls `python:3.12-slim` once. |

## Troubleshooting

- Print `decide(identity, tool, level, untrusted)` for the case you are debugging; the verdict carries its reason.
- `audit.verify()` returning False after your change means an entry was written outside `append()`.

## Production checklist

- [ ] Authorization uses the caller's identity on every call
- [ ] Injection is tested by effect
- [ ] Side effects behind untrusted content need approval
- [ ] Loops are bounded
- [ ] Approvals are bound to the exact proposal
- [ ] Audit is tamper-evident
- [ ] Untrusted code has no network

## Challenges

1. Add a P3 tool (submit) and a test that it always needs approval.
2. Add a case where the injection arrives through a tool result rather than a document.
3. Fill in `docs/templates/threat-model.md` for this agent.
