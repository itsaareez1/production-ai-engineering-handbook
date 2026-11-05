# Decisions

Short records of the choices that shape this repository. Each one
names what was decided, why, and what would change it.

## D1. No continuous integration

**Decision.** No GitHub Actions, no hosted runners, no scheduled or
deployment workflows, no paid testing infrastructure.
**Why.** The repository is free to maintain and free to fork. A
documented manual process ([VERIFICATION.md](VERIFICATION.md)) gives
the same evidence on a laptop in minutes.
**Revisit if** the project gains regular outside contributors; a fork
may add CI without changing any code.

## D2. A deterministic mock provider by default

**Decision.** Every test, lab, and listing runs on `MockProvider`.
**Why.** Readers can run everything with no account and no cost, and
failure paths can be injected exactly. A test that depends on a paid,
non-deterministic API is neither free nor repeatable.
**Consequence.** Numbers produced with the mock (for example judge
agreement) demonstrate the machinery, not model quality. The labs say
so wherever it matters.

## D3. PostgreSQL with pgvector, plus an in-memory store

**Decision.** One database for documents, permissions, chunks,
records, and audit; an in-memory store with the same interface.
**Why.** Permissions become a join rather than a synchronisation
problem, and there is one system to back up (Chapter 14). The memory
store keeps the tests fast and dependency-free.

## D4. Filters inside retrieval

**Decision.** ACL and document-status predicates run inside both
searches, before ranking.
**Why.** Filtering after ranking can leak through counts, timings, and
truncated result sets, and it starves the ranker (Chapter 16).

## D5. Hashing embeddings in the reference implementation

**Decision.** A 256-dimension feature-hashing embedder.
**Why.** Deterministic, offline, and free. It is weak at paraphrase,
and Lab 1 shows the miss rather than hiding it. Replace it with a real
embedding model in production; the store and evaluation do not change.

## D6. One bounded repair, then escalate

**Decision.** An answer that fails validation gets exactly one repair
attempt with the problems listed; a second failure escalates.
**Why.** Unbounded repair loops cost money and hide systematic faults
(Chapter 23).

## D7. Licensing

**Decision.** The code is MIT-licensed. The book's text, figures, and
manuscript are not in this repository and are not covered by the code
license.
**Status.** The license choice is the author's to confirm before the
book is published.
