"""Listing 6.1. Rules-first routing with a model fallback and
measurement of the split.

Chapter 6, When AI Should Not Be Used.
Verified by execution with a stubbed model.
Run with: python run.py 6.1
"""
import re
from collections import Counter

RULES = [  # (queue, compiled pattern)
    ("billing", re.compile(
        r"\b(invoice|refund|charge|receipt)\b", re.I)),
    ("access", re.compile(
        r"\b(password|login|locked out|2fa|mfa)\b", re.I)),
    ("hardware", re.compile(
        r"\b(laptop|monitor|keyboard|docking)\b", re.I)),
]


def route_by_rule(ticket: dict):
    text = f"{ticket['subject']} {ticket['body']}"
    for queue, pattern in RULES:
        if pattern.search(text):
            return queue
    return None


def route_by_model(ticket: dict) -> str:
    # Stub: a real call would go through the gateway with a fixed
    # output schema listing the six allowed queues.
    return "general"


def route(ticket: dict, stats: Counter) -> str:
    queue = route_by_rule(ticket)
    if queue:
        stats["rule"] += 1
        return queue
    stats["model"] += 1
    return route_by_model(ticket)


if __name__ == "__main__":
    tickets = [
        {"subject": "Refund for duplicate charge", "body": "..."},
        {"subject": "Locked out after MFA reset", "body": "..."},
        {"subject": "help", "body": "nothing works since yesterday"},
        {"subject": "New docking station",
         "body": "monitor not detected"},
    ]
    stats = Counter()
    for t in tickets:
        print(route(t, stats), "<-", t["subject"])
    print(dict(stats))
