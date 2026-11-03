"""Listing 17.1. Citation verification: label resolution and span
support.

Chapter 17, Context Assembly and Citation. Verified by execution.
Run with: python run.py 17.1
"""
import re


def words(s: str) -> list:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split()


def span_supported(claim: str, passage: str,
                   min_overlap: float = 0.6) -> bool:
    """Crude but useful: fraction of the claim's content words in
    the passage."""
    cw = [w for w in words(claim) if len(w) > 3]
    if not cw:
        return True
    pw = set(words(passage))
    return sum(1 for w in cw if w in pw) / len(cw) >= min_overlap


def verify_citations(answer: dict, context: dict) -> list:
    """context maps label -> passage text for labels actually sent
    to the model."""
    problems = []
    for label in answer["citations"]:
        if label not in context:
            problems.append(f"citation not in context: {label}")
    if answer["supported"] and not answer["citations"]:
        problems.append("supported answer has no citations")
    cited_text = " ".join(context[l] for l in answer["citations"]
                          if l in context)
    if answer["supported"] and cited_text:
        for sentence in re.split(r"(?<=[.!?])\s+", answer["answer"]):
            if sentence and not span_supported(sentence, cited_text):
                problems.append(
                    f"sentence not supported: {sentence!r}")
    return problems


if __name__ == "__main__":
    context = {
        "policy-leave/4.2@2026-06-01":
            "Unused annual leave may be carried forward up to five "
            "days into the next leave year, subject to manager "
            "approval.",
        "wiki/hr-faq/12@2026-03-14":
            "Questions about leave balances should go to HR via a "
            "ticket.",
    }
    good = {"answer": "Up to five days of unused annual leave may "
                      "be carried forward, subject to manager "
                      "approval.",
            "citations": ["policy-leave/4.2@2026-06-01"],
            "supported": True}
    bad = {"answer": "Up to five days may be carried forward. "
                     "Contractors are excluded.",
           "citations": ["policy-leave/4.2@2026-06-01",
                         "policy-leave/4.3@2026-06-01"],
           "supported": True}
    print("good:", verify_citations(good, context) or "ok")
    print("bad: ", verify_citations(bad, context))
