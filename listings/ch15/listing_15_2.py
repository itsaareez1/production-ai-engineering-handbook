"""Listing 15.2. Reciprocal rank fusion of keyword and semantic
rankings.

Chapter 15, Hybrid Retrieval. Verified by execution.
Run with: python run.py 15.2
"""


def rrf(rankings: list, k: int = 60) -> list:
    scores: dict = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


if __name__ == "__main__":
    query = "carry over unused leave"
    # Illustrative rankings, not the output of the earlier listings.
    keyword_ranking = ["leave-4.3", "leave-4.2", "forms-hr"]
    semantic_ranking = ["leave-4.2", "expenses-3", "leave-4.3"]
    for doc, score in rrf([keyword_ranking, semantic_ranking]):
        print(f"{score:.4f}  {doc}")
