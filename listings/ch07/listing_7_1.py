"""Listing 7.1. Sizing a self-hosted model: weights, KV cache, concurrency.

Chapter 7, Foundation Models and Inference. Verified by execution.
Every hardware figure below is an illustrative assumption for the
arithmetic, not a vendor specification; substitute the numbers for the
model and GPU you are actually evaluating.
Run with: python run.py 7.1
"""
from dataclasses import dataclass

GB = 1e9
BYTES = {"fp16": 2.0, "bf16": 2.0, "int8": 1.0, "int4": 0.5}


@dataclass(frozen=True)
class Model:
    name: str
    params_b: float      # parameters, billions
    layers: int
    kv_heads: int        # key/value heads (fewer than query heads
    head_dim: int        # when grouped-query attention is used)


@dataclass(frozen=True)
class Gpu:
    name: str
    memory_gb: float
    bandwidth_gbs: float  # memory bandwidth, GB/s
    usd_per_hour: float


def weights_gb(m: Model, precision: str) -> float:
    return m.params_b * 1e9 * BYTES[precision] / GB


def kv_bytes_per_token(m: Model, precision: str = "fp16") -> float:
    # one key and one value vector per layer per KV head
    return 2 * m.layers * m.kv_heads * m.head_dim * BYTES[precision]


def max_sequences(m: Model, g: Gpu, n_gpus: int, precision: str,
                  context: int, reserve: float = 0.10) -> int:
    """Concurrent sequences of `context` tokens that fit after the
    weights, keeping `reserve` of memory for activations/runtime."""
    free = n_gpus * g.memory_gb * (1 - reserve) - weights_gb(
        m, precision)
    per_seq = kv_bytes_per_token(m) * context / GB
    return max(0, int(free // per_seq))


def decode_tokens_per_s(m: Model, g: Gpu, n_gpus: int,
                        precision: str, batch: int,
                        avg_context: int) -> float:
    """Memory-bound upper bound: each decode step reads the weights
    once and every sequence's KV cache once. Ignores compute limits,
    so real throughput is lower; use it to compare options."""
    step_bytes = (weights_gb(m, precision) * GB
                  + batch * avg_context * kv_bytes_per_token(m))
    step_s = step_bytes / (n_gpus * g.bandwidth_gbs * GB)
    return batch / step_s


def usd_per_million(g: Gpu, n_gpus: int, tokens_per_s: float,
                    utilization: float) -> float:
    per_hour = tokens_per_s * 3600 * utilization
    return n_gpus * g.usd_per_hour / per_hour * 1e6


SMALL = Model("8B-class", 8.0, 32, 8, 128)
LARGE = Model("70B-class", 70.0, 80, 8, 128)
G24 = Gpu("24 GB GPU", 24, 300, 0.80)
G80 = Gpu("80 GB GPU", 80, 3000, 3.50)

if __name__ == "__main__":
    for m in (SMALL, LARGE):
        kv = kv_bytes_per_token(m) / 1024
        print(f"{m.name}: KV cache {kv:.0f} KiB/token (fp16); "
              f"weights fp16 {weights_gb(m, 'fp16'):.0f} GB, "
              f"int8 {weights_gb(m, 'int8'):.0f} GB, "
              f"int4 {weights_gb(m, 'int4'):.0f} GB")
    print()
    cases = [(SMALL, G24, 1, "fp16"), (SMALL, G24, 1, "int4"),
             (SMALL, G80, 1, "fp16"), (LARGE, G80, 1, "fp16"),
             (LARGE, G80, 2, "fp16"), (LARGE, G80, 1, "int4")]
    for m, g, n, p in cases:
        seqs = max_sequences(m, g, n, p, context=8192)
        label = f"{m.name} {p} on {n} x {g.name}"
        if seqs == 0:
            print(f"{label}: does not fit with an 8k context")
            continue
        batch = min(seqs, 32)
        tps = decode_tokens_per_s(m, g, n, p, batch, 4096)
        cost = usd_per_million(g, n, tps, utilization=0.5)
        print(f"{label}: {seqs} x 8k sequences fit; "
              f"batch {batch} <= {tps:,.0f} tok/s; "
              f"~${cost:.2f}/M output tokens at 50% use")
