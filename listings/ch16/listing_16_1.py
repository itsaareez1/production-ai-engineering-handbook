"""Listing 16.1. Reranking a fused candidate list with a scorer, and
measuring the effect.

Chapter 16, Filtering, Reranking, and Query Rewriting.
Verified by execution with a stubbed scorer.
Run with: python run.py 16.1
"""


def recall_at_k(results: list, relevant: list, k: int) -> float:
    """Same function as Listing 13.1, repeated here so the listing
    is standalone."""
    hits = sum(1 for res, rel in zip(results, relevant)
               if set(res[:k]) & rel)
    return hits / len(results)


def rerank(query: str, candidates: list, scorer, keep: int) -> list:
    scored = [(doc, scorer(query, doc)) for doc in candidates]
    scored.sort(key=lambda x: -x[1])
    return [doc for doc, _ in scored[:keep]]


def stub_scorer(query: str, doc: str) -> float:
    # A real cross-encoder reads (query, passage) and returns a
    # relevance score.
    return {"leave-4.2": 0.97,
            "leave-4.3": 0.61,
            "forms-hr": 0.40}.get(doc, 0.05)


if __name__ == "__main__":
    fused = ["leave-1.0", "leave-2.1", "leave-4.3", "leave-3.0",
             "forms-hr", "leave-2.2", "leave-1.1", "leave-3.1",
             "leave-4.2", "leave-5.0"]
    relevant = [{"leave-4.2"}]
    before = recall_at_k([fused], relevant, k=5)
    reranked = rerank(
        "carry over unused leave", fused, stub_scorer, keep=5)
    after = recall_at_k([reranked], relevant, k=5)
    print(f"recall@5 before rerank: {before:.0%}, "
          f"after: {after:.0%}")
    print("top 3 after rerank:", reranked[:3])
