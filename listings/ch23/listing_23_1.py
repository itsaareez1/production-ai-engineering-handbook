"""Listing 23.1. A ticket-triage state machine with a single,
validated model decision.

Chapter 23, The Deterministic Shell.
Verified by execution with a stubbed model.
Run with: python run.py 23.1
"""
import re
from enum import Enum, auto


class State(Enum):
    RECEIVED = auto()
    CLASSIFIED = auto()
    NEEDS_REVIEW = auto()
    ASSIGNED = auto()


QUEUES = {"billing", "access", "hardware", "general"}
RULES = [
    ("billing", re.compile(r"\b(invoice|refund|charge)\b", re.I)),
    ("access", re.compile(r"\b(password|login|mfa)\b", re.I)),
]
CONFIDENCE_FLOOR = 0.75


class Ticket:
    def __init__(self, tid, text):
        self.id, self.text, self.state = tid, text, State.RECEIVED
        self.queue, self.log = None, []


def classify_by_rule(text):
    for q, pat in RULES:
        if pat.search(text):
            return q
    return None


def classify_by_model(model, text):
    # {"queue": str, "confidence": float}
    out = model.classify(text)
    q, c = out.get("queue"), float(out.get("confidence", 0))
    if q not in QUEUES:  # validation: unknown class -> reject
        return None, 0.0
    return q, c


def transition(ticket: Ticket, model):
    assert ticket.state is State.RECEIVED
    q = classify_by_rule(ticket.text)
    if q:
        ticket.queue, ticket.state = q, State.CLASSIFIED
        ticket.log.append("rule")
    else:
        q, c = classify_by_model(model, ticket.text)
        if q and c >= CONFIDENCE_FLOOR:
            ticket.queue, ticket.state = q, State.CLASSIFIED
            ticket.log.append(f"model:{c:.2f}")
        else:
            ticket.state = State.NEEDS_REVIEW
            ticket.log.append(f"review:{q}:{c:.2f}")
    if ticket.state is State.CLASSIFIED:
        # Deterministic side effect goes here.
        ticket.state = State.ASSIGNED
    return ticket


class StubModel:
    def classify(self, text):
        t = text.lower()
        if "monitor" in t:
            return {"queue": "hardware", "confidence": 0.91}
        if "printer" in t:
            return {"queue": "facilities", "confidence": 0.88}
        return {"queue": "general", "confidence": 0.55}


if __name__ == "__main__":
    for tid, text in [("1", "Refund for a duplicate charge"),
                      ("2", "Second monitor not detected"),
                      ("3", "Printer on floor 3 jammed"),
                      ("4", "nothing works")]:
        t = transition(Ticket(tid, text), StubModel())
        print(tid, t.state.name, t.queue, t.log)
