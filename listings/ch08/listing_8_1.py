"""Listing 8.1. Cost per request under illustrative prices, with
caching and retry effects.

Chapter 8, Model Selection. Verified by execution. Prices are
placeholders; substitute current provider prices.
Run with: python run.py 8.1
"""


def cost_per_request(price_in, price_out, tokens_in, tokens_out,
                     cached_tokens=0, cache_discount=0.9,
                     retry_rate=0.0):
    """Prices are USD per million tokens. cache_discount is the
    fraction of the input price saved on cached tokens. retry_rate
    is the mean number of extra full attempts per request."""
    uncached = tokens_in - cached_tokens
    input_cost = (
        uncached * price_in
        + cached_tokens * price_in * (1 - cache_discount)
    ) / 1e6
    output_cost = tokens_out * price_out / 1e6
    return (input_cost + output_cost) * (1 + retry_rate)


profile = dict(tokens_in=14_200, tokens_out=600)

large = cost_per_request(3.00, 15.00, **profile)
mid = cost_per_request(0.80, 4.00, **profile, retry_rate=0.08)
large_cached = cost_per_request(
    3.00, 15.00, **profile, cached_tokens=2_000
)

print(f"large: ${large:.4f}  mid (8% retries): ${mid:.4f}  "
      f"large w/ cached prefix: ${large_cached:.4f}")
print(f"monthly at 50k requests: large ${large * 50_000:,.0f}, "
      f"mid ${mid * 50_000:,.0f}")
