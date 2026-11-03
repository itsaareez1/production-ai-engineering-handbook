"""Listing 13.1. Retrieval evaluation: recall@k and mean reciprocal
rank over a labeled set.

Chapter 13, Retrieval-Augmented Generation.
Verified by execution with a stubbed retriever.
Run with: python run.py 13.1
"""


def recall_at_k(results: list, relevant: list, k: int) -> float:
    hits = sum(1 for res, rel in zip(results, relevant)
               if set(res[:k]) & rel)
    return hits / len(results)


def mrr(results: list, relevant: list) -> float:
    total = 0.0
    for res, rel in zip(results, relevant):
        for rank, doc in enumerate(res, start=1):
            if doc in rel:
                total += 1 / rank
                break
    return total / len(results)


# A labeled evaluation set: question id -> relevant chunk ids.
EVAL = [
    ("q1", {"leave-4.2"}),
    ("q2", {"expenses-3.1", "expenses-3.2"}),
    ("q3", {"vpn-setup-1"}),
    ("q4", {"leave-4.2"}),
]


def stub_retriever(qid: str) -> list:
    return {
        "q1": ["leave-1.0", "leave-4.2", "leave-4.3"],
        "q2": ["expenses-3.2", "expenses-1.0", "travel-2.1"],
        # q3's relevant chunk is missing from the results entirely.
        "q3": ["wifi-1", "vpn-faq", "printer-2"],
        "q4": ["leave-4.1", "leave-4.3", "leave-2.0", "leave-4.2"],
    }[qid]


if __name__ == "__main__":
    results = [stub_retriever(q) for q, _ in EVAL]
    relevant = [rel for _, rel in EVAL]
    for k in (1, 3, 5):
        print(f"recall@{k}: {recall_at_k(results, relevant, k):.2f}")
    print(f"MRR: {mrr(results, relevant):.2f}")
