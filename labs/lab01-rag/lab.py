"""Lab 1: Build a production RAG application (Chapters 13-18).

Runs offline. Steps: ingest with structure-aware chunking and an
injection scan; measure retrieval (semantic, keyword, fused, reranked)
with recall@k and MRR; prove that ACL and status filters run inside
retrieval; verify citations by label and by sentence.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repository root

from atlas.core.identity import DIRECTORY
from atlas.corpus import load_corpus
from atlas.retrieval.context import verify_citations
from atlas.retrieval.text import Document, chunk_document, rrf
from atlas.testing import CORPUS, ROOT, make_atlas

atlas = make_atlas(seed=False)

print("== Step 1: ingest")
all_docs = list(load_corpus(CORPUS))
for doc in all_docs:
    r = atlas.ingest(doc)
    print(f"  {r.doc_id:<16} {r.outcome:<12} chunks={r.chunks} {', '.join(r.reasons)}")

print("\n== Step 2: structure-aware chunks keep tables and heading paths")
exp = next(d for d in load_corpus(CORPUS) if d.doc_id == "policy-expenses")
for c in chunk_document(exp):
    print(f"  {c.label}  [{c.heading_path}]  {c.text.splitlines()[0][:50]}")

print("\n== Step 3: retrieval evaluation (recall@5, MRR)")
# Seven documents cannot make retrieval fail, so add 120 near-miss
# distractor pages with overlapping vocabulary (seeded: same every run).
rng = random.Random(3)
TOPICS = ["leave of absence for jury duty", "carry-on baggage allowance on flights",
          "unused office equipment returns", "meal vouchers in the canteen",
          "laptop bag reimbursement", "password manager rollout", "form HR-2 for name changes",
          "hotel booking portal outages", "annual performance review days",
          "carry over of training budget", "taxi app account setup",
          "expense report template EX-1", "parental leave pay rates",
          "days of remote work per week", "end of year office closure",
          "manager approval workflows for purchases", "reset of desk phone voicemail",
          "business travel insurance", "senior engineer career ladder", "salary payment dates"]
FILLER = ["policy", "days", "form", "request", "manager", "approval", "year", "limit", "euros"]
for i in range(120):
    t = rng.choice(TOPICS)
    body = (f"# {t.title()}\n\n## Details {i}\n\nThis page covers {t}. "
            + " ".join(rng.sample(t.split() * 3 + FILLER, 12)) + ".")
    noise = Document(f"noise-{i:03d}", t.title(), body, frozenset({"all-staff"}),
                     source="wiki/noise", updated="2026-01-01")
    all_docs.append(noise)
    atlas.ingest(noise)
items = [json.loads(x) for x in
         (ROOT / "examples/evaluation/retrieval_set.jsonl").read_text().splitlines()]


def ranked_docs(q, user, mode):
    who = DIRECTORY[user]
    vec = atlas.store.search_vector(atlas.embedder.embed([q])[0], who.groups, 40).ranked
    kw = atlas.store.search_keyword(q, who.groups, 40).ranked
    if mode == "semantic":
        ids = [c.chunk_id for c, _ in vec]
    elif mode == "keyword":
        ids = [c.chunk_id for c, _ in kw]
    else:
        ids = [cid for cid, _ in rrf([[c.chunk_id for c, _ in vec], [c.chunk_id for c, _ in kw]])]
        if mode == "fused+rerank":
            by = {c.chunk_id: c for c, _ in vec + kw}
            sc = atlas.reranker.score(q, [by[i].heading_path + " " + by[i].text for i in ids])
            ids = [i for _, i in sorted(zip(sc, ids), key=lambda t: -t[0])]
    docs = []
    for cid in ids:
        d = cid.split("#")[0]
        if d not in docs:
            docs.append(d)
    return docs


for mode in ("semantic", "keyword", "fused", "fused+rerank"):
    hits, rr = 0, 0.0
    for it in items:
        docs = ranked_docs(it["q"], it["user"], mode)
        ranks = [docs.index(r) + 1 for r in it["relevant"] if r in docs]
        hits += any(r <= 5 for r in ranks)
        rr += 1 / min(ranks) if ranks else 0
    print(f"  {mode:<13} recall@5={hits / len(items):.2f}  MRR={rr / len(items):.2f}")
for it in items:
    docs = ranked_docs(it["q"], it["user"], "fused+rerank")
    if docs[:1] != it["relevant"][:1]:
        rank = docs.index(it["relevant"][0]) + 1 if it["relevant"][0] in docs else None
        print(f"  not first after rerank: {it['q']!r} (rank {rank})")

print("\n== Step 4: filters run inside retrieval")
for user in ("alice", "sam"):
    res = atlas.store.search_keyword("salary band senior engineer", DIRECTORY[user].groups, 10)
    print(f"  {user}: docs={sorted({c.doc_id for c, _ in res.ranked})} "
          f"acl_filtered={res.acl_filtered}")
res = atlas.store.search_keyword("carry over unused leave", DIRECTORY["alice"].groups, 10)
print(f"  superseded excluded: {'policy-leave-v6' not in {c.doc_id for c, _ in res.ranked}} "
      f"(status_filtered={res.status_filtered})")

print("\n== Step 5: citation verification")
r = atlas.ask("How many days of unused leave can I carry over?", DIRECTORY["alice"])
print(f"  answer: {r.answer['answer']}\n  cites:  {r.answer['citations']}")
chunks = {c.label: c for d in all_docs for c in chunk_document(d)}
labels = {s["label"]: chunks[s["label"]] for s in r.sources}   # what was in the context
bad = dict(r.answer, answer=r.answer["answer"] + " Contractors are excluded.")
print(f"  good answer problems: {verify_citations(r.answer, labels)}")
print(f"  appended claim:       {verify_citations(bad, labels)}")
ghost = dict(r.answer, citations=["policy-leave-v6#0@2024-01-10"])
print(f"  stale citation:       {verify_citations(ghost, labels)}")
