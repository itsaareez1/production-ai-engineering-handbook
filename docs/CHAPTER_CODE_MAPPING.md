# Chapter-to-code mapping

Where to find the companion code for every chapter of *The Production AI Engineering Handbook*. Paths are relative to the repository root. Chapters with nothing listed are conceptual and have no code.

## Listing status key

| Code | Meaning |
|---|---|
| **EV** | Executable and verified: executed, output checked (see [VERIFICATION.md](VERIFICATION.md)) |
| **EC** | Executable, needs external credentials (a paid model provider); not run by the test suite |
| **PS** | Illustrative pseudocode |
| **CF** | Configuration or protocol example, validated by a checker or by running it |
| **IC** | Incomplete or needs correction |

The repository contains no PS or IC listings. The only EC code is the optional `AnthropicProvider` and `OpenAIProvider` adapters in `atlas/gateway/providers.py`; everything else runs on the deterministic mock provider.

## Part I: From AI Demo to Engineered System

### Chapter 1. From AI Demo to Production System

Conceptual chapter; no code.

### Chapter 2. What AI Engineering Actually Means

Conceptual chapter; no code.

### Chapter 3. The Anatomy of an AI Application

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 3.1 | `listings/ch03/listing_3_1.py` | EV | `python run.py 3.1` |

- **Atlas implementation:** `atlas/service.py`
- **Tests:** `tests/unit/test_gateway_and_service.py`

## Part II: Models and Context

### Chapter 4. Models, Applications, Workflows, and Agents

Conceptual chapter; no code.

### Chapter 5. Requirements Before Models

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 5.1 | `listings/ch05/listing_5_1.py` | EV | `python run.py 5.1` |

- **Atlas implementation:** `atlas/security/controls.py (Redactor)`, `atlas/core/config.py`
- **Tests:** `tests/security/test_security.py`
- **Also:** `docs/templates/threat-model.md`

### Chapter 6. When AI Should Not Be Used

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 6.1 | `listings/ch06/listing_6_1.py` | EV | `python run.py 6.1` |


### Chapter 7. Foundation Models and Inference

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 7.1 | `listings/ch07/listing_7_1.py` | EV | `python run.py 7.1` |

- **Also:** `docker-compose.yml (inference profile)`

### Chapter 8. Choosing a Model

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 8.1 | `listings/ch08/listing_8_1.py` | EV | `python run.py 8.1` |


### Chapter 9. Model Gateways, Routing, and Fallbacks

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 9.1 | `listings/ch09/listing_9_1.py` | EV | `python run.py 9.1` |

- **Atlas implementation:** `atlas/gateway/gateway.py`, `atlas/gateway/providers.py`
- **Tests:** `tests/unit/test_gateway_and_service.py`
- **Labs:** [`labs/lab02-model-gateway`](../labs/lab02-model-gateway)

### Chapter 10. Context Windows and Context Engineering

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 10.1 | `listings/ch10/listing_10_1.py` | EV | `python run.py 10.1` |

- **Atlas implementation:** `atlas/retrieval/context.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)

### Chapter 11. Instruction Engineering

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 11.1 | `listings/ch11/listing_11_1.py` | EV | `python run.py 11.1` |

- **Atlas implementation:** `atlas/prompts/answer_v1.md`

### Chapter 12. Structured Outputs

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 12.1 | `listings/ch12/listing_12_1.py` | EV | `python run.py 12.1` |

- **Atlas implementation:** `atlas/validation.py`, `atlas/gateway/providers.py (strict_schema)`
- **Tests:** `tests/test_api.py`

## Part III: Knowledge and Retrieval

### Chapter 13. Retrieval-Augmented Generation

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 13.1 | `listings/ch13/listing_13_1.py` | EV | `python run.py 13.1` |

- **Atlas implementation:** `atlas/service.py (ask)`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)

### Chapter 14. Embeddings and Vector Stores

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 14.1 | `listings/ch14/listing_14_1.py` | EV | `python run.py 14.1` |
| Listing 14.2 | `listings/ch14/listing_14_2.sql` | EV | `python listings/ch14/verify_14_2.py <url>` |

- **Atlas implementation:** `atlas/retrieval/text.py (HashingEmbedder)`, `atlas/retrieval/store.py`, `atlas/db/migrations/001_init.sql`
- **Tests:** `tests/integration/test_postgres.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)
- **Also:** `listings/ch14/verify_14_2.py`

### Chapter 15. Semantic, Keyword, and Hybrid Retrieval

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 15.1 | `listings/ch15/listing_15_1.py` | EV | `python run.py 15.1` |
| Listing 15.2 | `listings/ch15/listing_15_2.py` | EV | `python run.py 15.2` |
| Listing 15.3 | `listings/ch15/listing_15_3.py` | EV | `python run.py 15.3` |

- **Atlas implementation:** `atlas/retrieval/store.py`, `atlas/retrieval/text.py (rrf)`
- **Tests:** `tests/unit/test_core_and_retrieval.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)
- **Also:** `examples/evaluation/retrieval_set.jsonl`

### Chapter 16. Filtering, Reranking, and Query Rewriting

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 16.1 | `listings/ch16/listing_16_1.py` | EV | `python run.py 16.1` |

- **Atlas implementation:** `atlas/retrieval/text.py (LexicalReranker)`, `atlas/retrieval/store.py (ACL, status)`
- **Tests:** `tests/unit/test_core_and_retrieval.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)

### Chapter 17. Context Assembly and Citations

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 17.1 | `listings/ch17/listing_17_1.py` | EV | `python run.py 17.1` |

- **Atlas implementation:** `atlas/retrieval/context.py`
- **Tests:** `tests/unit/test_core_and_retrieval.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)

### Chapter 18. Knowledge Pipelines and the System of Record

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 18.1 | `listings/ch18/listing_18_1.py` | EV | `python run.py 18.1` |
| Listing 18.2 | `listings/ch18/listing_18_2.py` | EV | `python run.py 18.2` |

- **Atlas implementation:** `atlas/retrieval/text.py (chunk_document)`, `atlas/corpus.py`, `atlas/service.py (ingest, reconcile)`
- **Tests:** `tests/unit/test_core_and_retrieval.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)
- **Also:** `examples/corpus/`

## Part IV: Tools and Workflows

### Chapter 19. Function and Tool Calling

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 19.1 | `listings/ch19/listing_19_1.py` | EV | `python run.py 19.1` |

- **Atlas implementation:** `atlas/agents/agent.py (Tool)`
- **Tests:** `tests/unit/test_agent_and_evaluation.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 20. Integrating APIs and External Systems

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 20.1 | `listings/ch20/listing_20_1.py` | EV | `python run.py 20.1` |

- **Atlas implementation:** `atlas/security/controls.py (check_egress)`
- **Tests:** `tests/security/test_security.py`

### Chapter 21. MCP and Modern Tool Access

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 21.1 | `listings/ch21/listing_21_1.jsonc` | CF | `python listings/ch21/validate_21_1.py` |

- **Also:** `listings/ch21/validate_21_1.py`

### Chapter 22. Designing AI Workflows

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 22.1 | `listings/ch22/listing_22_1.py` | EV | `python run.py 22.1` |


### Chapter 23. Deterministic Software Around Probabilistic Components

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 23.1 | `listings/ch23/listing_23_1.py` | EV | `python run.py 23.1` |


### Chapter 24. State, Idempotency, Retries, and Failure Handling

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 24.1 | `listings/ch24/listing_24_1.py` | EV | `python run.py 24.1` |

- **Atlas implementation:** `atlas/gateway/gateway.py (retries)`, `atlas/agents/records.py (idempotency)`
- **Tests:** `tests/unit/test_agent_and_evaluation.py`
- **Labs:** [`labs/lab02-model-gateway`](../labs/lab02-model-gateway)

## Part V: Agents

### Chapter 25. What an AI Agent Is (and Is Not)

Conceptual chapter; no code.

### Chapter 26. Agent Architecture

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 26.1 | `listings/ch26/listing_26_1.py` | EV | `python run.py 26.1` |

- **Atlas implementation:** `atlas/agents/agent.py (TicketAgent)`
- **Tests:** `tests/unit/test_agent_and_evaluation.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 27. Agent Memory and State

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 27.1 | `listings/ch27/listing_27_1.py` | EV | `python run.py 27.1` |

- **Atlas implementation:** `atlas/agents/records.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 28. Tools, Permissions, and Boundaries

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 28.1 | `listings/ch28/listing_28_1.py` | EV | `python run.py 28.1` |

- **Atlas implementation:** `atlas/agents/agent.py (decide)`
- **Tests:** `tests/unit/test_agent_and_evaluation.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 29. Human-in-the-Loop Agents

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 29.1 | `listings/ch29/listing_29_1.py` | EV | `python run.py 29.1` |

- **Atlas implementation:** `atlas/agents/agent.py (Approvals)`
- **Tests:** `tests/unit/test_agent_and_evaluation.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 30. Multi-Agent Systems

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 30.1 | `listings/ch30/listing_30_1.py` | EV | `python run.py 30.1` |


### Chapter 31. When Agents Are the Wrong Choice

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 31.1 | `listings/ch31/listing_31_1.py` | EV | `python run.py 31.1` |


## Part VI: Evaluation and Reliability

### Chapter 32. Why AI Applications Fail

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 32.1 | `listings/ch32/listing_32_1.py` | EV | `python run.py 32.1` |

- **Atlas implementation:** `atlas/core/observability.py`
- **Labs:** [`labs/lab06-observability`](../labs/lab06-observability)

### Chapter 33. Testing AI Applications

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 33.1 | `listings/ch33/listing_33_1.py` | EV | `python run.py 33.1` |

- **Atlas implementation:** `atlas/evaluation/harness.py`
- **Tests:** `tests/`
- **Labs:** [`labs/lab03-evaluation`](../labs/lab03-evaluation)

### Chapter 34. Golden Sets and Evaluation Datasets

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 34.1 | `listings/ch34/listing_34_1.py` | EV | `python run.py 34.1` |

- **Atlas implementation:** `atlas/evaluation/harness.py (load_golden)`
- **Labs:** [`labs/lab03-evaluation`](../labs/lab03-evaluation)
- **Also:** `examples/evaluation/golden_set.jsonl`

### Chapter 35. Measuring AI Quality

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 35.1 | `listings/ch35/listing_35_1.py` | EV | `python run.py 35.1` |

- **Atlas implementation:** `atlas/evaluation/harness.py (wilson, cohen_kappa)`
- **Tests:** `tests/unit/test_agent_and_evaluation.py`
- **Labs:** [`labs/lab03-evaluation`](../labs/lab03-evaluation)

### Chapter 36. Hallucinations, Grounding, and Verification

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 36.1 | `listings/ch36/listing_36_1.py` | EV | `python run.py 36.1` |

- **Atlas implementation:** `atlas/retrieval/context.py (verify_citations)`
- **Tests:** `tests/unit/test_core_and_retrieval.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag)

### Chapter 37. Reliability Engineering for AI

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 37.1 | `listings/ch37/listing_37_1.py` | EV | `python run.py 37.1` |

- **Atlas implementation:** `atlas/gateway/gateway.py (breakers)`
- **Labs:** [`labs/lab06-observability`](../labs/lab06-observability)

### Chapter 38. Regression Testing and Continuous Evaluation

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 38.1 | `listings/ch38/listing_38_1.py` | EV | `python run.py 38.1` |

- **Atlas implementation:** `atlas/evaluation/harness.py (regression_gate)`
- **Tests:** `tests/unit/test_agent_and_evaluation.py`
- **Labs:** [`labs/lab03-evaluation`](../labs/lab03-evaluation)

## Part VII: Security

### Chapter 39. Prompt Injection

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 39.1 | `listings/ch39/listing_39_1.py` | EV | `python run.py 39.1` |

- **Atlas implementation:** `atlas/security/controls.py (scan_for_injection)`
- **Tests:** `tests/security/test_security.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 40. Indirect Injection and Untrusted Content

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 40.1 | `listings/ch40/listing_40_1.py` | EV | `python run.py 40.1` |

- **Atlas implementation:** `atlas/security/controls.py`, `atlas/service.py (quarantine)`
- **Tests:** `tests/security/test_security.py`
- **Labs:** [`labs/lab01-rag`](../labs/lab01-rag), [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 41. Data Security and Privacy

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 41.1 | `listings/ch41/listing_41_1.py` | EV | `python run.py 41.1` |

- **Atlas implementation:** `atlas/security/controls.py (Redactor)`
- **Tests:** `tests/security/test_security.py`

### Chapter 42. Identity, Authorization, and Least Privilege

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 42.1 | `listings/ch42/listing_42_1.py` | EV | `python run.py 42.1` |

- **Atlas implementation:** `atlas/core/identity.py`, `atlas/api/__init__.py`
- **Tests:** `tests/security/test_security.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)

### Chapter 43. Securing AI Agents and Tools

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 43.1 | `listings/ch43/listing_43_1.py` | EV | `python run.py 43.1` |
| Listing 43.2 | `listings/ch43/listing_43_2.py` | EV | `python run.py 43.2` |

- **Atlas implementation:** `atlas/agents/agent.py`, `atlas/agents/records.py (audit)`
- **Tests:** `tests/security/test_security.py`
- **Labs:** [`labs/lab04-agent-security`](../labs/lab04-agent-security)
- **Also:** `docs/templates/threat-model.md`

## Part VIII: Production Engineering

### Chapter 44. Deploying AI Applications

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 44.1 | `listings/ch44/Dockerfile, docker-compose.yml` | CF | `docker compose up --build` |

- **Atlas implementation:** `atlas/db/migrate.py`, `atlas/api/__init__.py`
- **Tests:** `tests/test_api.py`
- **Labs:** [`labs/lab05-deployment`](../labs/lab05-deployment)
- **Also:** `Dockerfile`, `docker-compose.yml`

### Chapter 45. Observability and Monitoring

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 45.1 | `listings/ch45/listing_45_1.py` | EV | `python run.py 45.1` |

- **Atlas implementation:** `atlas/core/observability.py`
- **Labs:** [`labs/lab06-observability`](../labs/lab06-observability)

### Chapter 46. Cost Engineering and Performance

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 46.1 | `listings/ch46/listing_46_1.py` | EV | `python run.py 46.1` |

- **Atlas implementation:** `atlas/gateway/gateway.py (Ledger, PRICES)`
- **Tests:** `tests/unit/test_gateway_and_service.py`
- **Labs:** [`labs/lab02-model-gateway`](../labs/lab02-model-gateway), [`labs/lab06-observability`](../labs/lab06-observability)

### Chapter 47. Scaling, Availability, and Resilience

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 47.1 | `listings/ch47/listing_47_1.py` | EV | `python run.py 47.1` |

- **Atlas implementation:** `atlas/gateway/gateway.py (fallback)`
- **Labs:** [`labs/lab05-deployment`](../labs/lab05-deployment), [`labs/lab07-production-readiness`](../labs/lab07-production-readiness)

### Chapter 48. AI CI/CD and Release Management

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 48.1 | `listings/ch48/listing_48_1.py` | EV | `python run.py 48.1` |

- **Atlas implementation:** `atlas/evaluation/harness.py (regression_gate)`
- **Labs:** [`labs/lab03-evaluation`](../labs/lab03-evaluation), [`labs/lab07-production-readiness`](../labs/lab07-production-readiness)
- **Also:** `docs/VERIFICATION.md`

## Part IX: Architecture and Ownership

### Chapter 49. Build, Buy, or Integrate

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 49.1 | `listings/ch49/listing_49_1.py` | EV | `python run.py 49.1` |


### Chapter 50. Production Architecture Patterns and Maintainability

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 50.1 | `listings/ch50/listing_50_1.py` | EV | `python run.py 50.1` |


### Chapter 51. Governance and Operational Ownership

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 51.1 | `listings/ch51/listing_51_1.py` | EV | `python run.py 51.1` |

- **Atlas implementation:** `atlas/agents/records.py (audit)`
- **Labs:** [`labs/lab07-production-readiness`](../labs/lab07-production-readiness)

### Chapter 52. The Complete Project: From Prototype to Production

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 52.1 | `listings/ch52/listing_52_1.py` | EV | `python run.py 52.1` |

- **Atlas implementation:** `atlas/ (the whole package)`
- **Tests:** `tests/`
- **Labs:** `lab01-rag … lab07-production-readiness`

### Chapter 53. The Production AI Readiness Review

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 53.1 | `listings/ch53/listing_53_1.py` | EV | `python run.py 53.1` |

- **Labs:** [`labs/lab07-production-readiness`](../labs/lab07-production-readiness)

### Chapter 54. The AI Engineering Implementation Roadmap

| Listing | File | Status | Run |
|---|---|---|---|
| Listing 54.1 | `listings/ch54/listing_54_1.py` | EV | `python run.py 54.1` |


## Appendices

| Appendix | Companion material |
|---|---|
| A. Production AI Checklist | `labs/lab07-production-readiness` executes the automatable items |
| B. AI Evaluation Template | `labs/lab03-evaluation/eval_report.md` is a filled example |
| C. Security Review Checklist | `docs/templates/threat-model.md` (C.5) |
| E. Cost Estimation Worksheet | `atlas/gateway/gateway.py` (`PRICES`, `Ledger`); Listing 46.1 |
| F. Troubleshooting Guide | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| K. Running the Companion Code | this repository; start with the [README](../README.md) |
| L. GPU and Model Deployment Reference | Listing 7.1; the `inference` profile in `docker-compose.yml` |
| N. Technology Stack Reference | the Atlas column of Table N.1 is this repository |
