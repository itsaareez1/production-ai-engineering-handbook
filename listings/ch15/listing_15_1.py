"""Listing 15.1. BM25 keyword scoring over a small corpus.

Chapter 15, Hybrid Retrieval. Verified by execution.
Run with: python run.py 15.1
"""
import math
import re
from collections import Counter


def tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9][a-z0-9\-]*", text.lower())


class BM25:
    def __init__(self, docs: dict, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tokens = {d: tokenize(t) for d, t in docs.items()}
        self.avg_len = (
            sum(len(t) for t in self.tokens.values()) / len(docs)
        )
        df = Counter()
        for toks in self.tokens.values():
            df.update(set(toks))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5))
                    for t, f in df.items()}

    def score(self, query: str, doc_id: str) -> float:
        toks = self.tokens[doc_id]
        tf = Counter(toks)
        length = len(toks)
        s = 0.0
        for q in tokenize(query):
            if q not in tf:
                continue
            num = tf[q] * (self.k1 + 1)
            den = tf[q] + self.k1 * (
                1 - self.b + self.b * length / self.avg_len
            )
            s += self.idf[q] * num / den
        return s

    def search(self, query: str, k: int = 5) -> list:
        ranked = sorted(
            ((d, self.score(query, d)) for d in self.tokens),
            key=lambda x: -x[1],
        )
        return [(d, s) for d, s in ranked[:k] if s > 0]


DOCS = {
    "leave-4.2": "Unused annual leave may be carried forward up to "
                 "five days.",
    "leave-4.3": "Carry-over is not permitted for contractors.",
    "forms-hr": "Use form HR-27 to request a leave carry-over "
                "exception.",
    "expenses-3": "Expense claims above the limit require form "
                  "FIN-9.",
}


if __name__ == "__main__":
    bm = BM25(DOCS)
    for q in ("form HR-27", "carry over unused leave"):
        print(q, "->",
              [(d, round(s, 2)) for d, s in bm.search(q, k=3)])
