"""Listing 3.1. A minimal AI application skeleton with a stubbed model.

Chapter 3, The Reference Architecture. Verified by execution.
Run with: python run.py 3.1
"""
import json
import time
from dataclasses import dataclass, field


# --- Gateway: knows models and budgets, nothing about invoices ---
class ModelGateway:
    def __init__(self, provider):
        self.provider = provider  # any object with .complete(prompt)
        self.calls = 0

    def complete(self, prompt: str, max_tokens: int = 512) -> str:
        self.calls += 1
        return self.provider.complete(prompt)


class StubProvider:
    """Stands in for a hosted model during tests."""

    def complete(self, prompt: str) -> str:
        return json.dumps({
            "supplier": "Acme Ltd",
            "total": 120.0,
            "lines": [
                {"desc": "Widget", "amount": 100.0},
                {"desc": "Shipping", "amount": 20.0},
            ],
        })


# --- Output validation: the model's output is untrusted input ---
def validate_invoice(raw: str) -> dict:
    data = json.loads(raw)
    for key in ("supplier", "total", "lines"):
        if key not in data:
            raise ValueError(f"missing field: {key}")
    line_sum = round(sum(l["amount"] for l in data["lines"]), 2)
    if line_sum != round(data["total"], 2):
        raise ValueError(
            f"line items {line_sum} != total {data['total']}"
        )
    return data


# --- Observability: one record per request ---
@dataclass
class RequestRecord:
    request_id: str
    outcome: str = "pending"
    latency_ms: float = 0.0
    notes: list = field(default_factory=list)


# --- Orchestration: control flow lives here, not in the model ---
def extract_invoice(
    text: str, gateway: ModelGateway, record: RequestRecord
):
    start = time.perf_counter()
    prompt = (
        "Extract supplier, total, and line items as JSON.\n\n" + text
    )
    try:
        result = validate_invoice(gateway.complete(prompt))
        record.outcome = "validated"
        return result
    except (ValueError, json.JSONDecodeError) as e:
        record.outcome = "needs_review"
        record.notes.append(str(e))
        return None
    finally:
        record.latency_ms = (time.perf_counter() - start) * 1000


if __name__ == "__main__":
    gw = ModelGateway(StubProvider())
    rec = RequestRecord(request_id="inv-001")
    result = extract_invoice(
        "INVOICE Acme Ltd ... total 120.00", gw, rec
    )
    print(rec.outcome, result["total"] if result else None, gw.calls)
