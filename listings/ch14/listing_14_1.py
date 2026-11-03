"""Listing 14.1. Cosine similarity and exact nearest-neighbor search.

Chapter 14, Embeddings and Vector Search. Verified by execution.
Run with: python run.py 14.1
"""
import numpy as np


def normalize(m: np.ndarray) -> np.ndarray:
    return m / np.linalg.norm(m, axis=-1, keepdims=True)


def top_k(query: np.ndarray, index: np.ndarray, k: int):
    """Rows and query are unit vectors: dot product is cosine
    similarity."""
    sims = index @ query
    order = np.argsort(-sims)[:k]
    return [(int(i), float(sims[i])) for i in order]


# Toy 4-dimensional "embeddings"; real ones have far more dimensions.
chunks = ["leave carry-over rules", "expense claim limits",
          "leave accrual during parental leave",
          "VPN setup on laptops"]
index = normalize(np.array([[0.9, 0.1, 0.4, 0.0],
                            [0.1, 0.9, 0.1, 0.1],
                            [0.8, 0.0, 0.7, 0.0],
                            [0.0, 0.1, 0.0, 0.9]]))
# "unused leave after parental?"
query = normalize(np.array([0.85, 0.05, 0.5, 0.0]))

for i, s in top_k(query, index, k=3):
    print(f"{s:.3f}  {chunks[i]}")
