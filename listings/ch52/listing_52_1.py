"""Listing 52.1. Atlas prototype path and production path side by
side, with stubs.

Chapter 52, The Atlas Case Study End to End.
Verified by execution.
Run with: python run.py 52.1
"""
import hashlib
import json

# ---- shared stubs -------------------------------------------------
INDEX = [  # chunk id, document, text, acl groups, status
    ("policy-leave/4.2@2026-06-01", "policy-leave",
     "Unused annual leave may be carried forward up to five days, "
     "subject to manager approval.", {"all-staff"}, "current"),
    ("policy-leave/4.2@2025-01-10", "policy-leave-old",
     "Unused annual leave may be carried forward up to ten days.",
     {"all-staff"}, "superseded"),
    ("policy-pay/3.1@2026-05-02", "policy-pay",
     "Salary bands: grade D 52-61k.", {"hr", "management"},
     "current"),
]


def stub_model(prompt: str) -> str:
    # Returns JSON when asked for it; free text otherwise. Cites
    # what it sees.
    if '"citations"' in prompt:
        if ("salary" in prompt.lower()
                and "Salary bands" not in prompt):
            return json.dumps({"answer": "", "citations": [],
                               "supported": False,
                               "confidence": "low",
                               "escalate": True})
        lbl = ("policy-leave/4.2@2026-06-01"
               if "2026-06-01" in prompt else "policy/ghost")
        return json.dumps({
            "answer": "Up to five days may be carried forward, "
                      "subject to manager approval.",
            "citations": [lbl], "supported": True,
            "confidence": "high", "escalate": False})
    # Trusts whatever it saw.
    return "You can carry over up to ten days of leave."


# ---- v0.1 prototype -----------------------------------------------
def prototype(question: str) -> str:
    # Top-5, no filters.
    chunks = [c for c in INDEX][:5]
    prompt = "\n".join(c[2] for c in chunks) + "\n\nQ: " + question
    # Displayed as-is.
    return stub_model(prompt)


# ---- v1.0 production ----------------------------------------------
INSTRUCTIONS = ("Answer only from labeled sources; cite labels; "
                "escalate if unsupported.")
# Chapter 11.
INSTR_HASH = hashlib.sha256(
    INSTRUCTIONS.encode()).hexdigest()[:8]


def production(question: str, groups: set) -> dict:
    # Chapter 45.
    trace = {"instructions": INSTR_HASH, "model": "m-2026-06",
             "index": "idx-0912", "spans": []}
    # Retrieval: ACL and status filters inside the query
    # (Chapters 14, 16).
    cands = [c for c in INDEX
             if c[3] & groups and c[4] == "current"]
    by_acl = sum(1 for c in INDEX if not c[3] & groups)
    by_status = sum(1 for c in INDEX
                    if c[3] & groups and c[4] != "current")
    trace["spans"].append({"retrieval": {
        "candidates": len(cands),
        "filtered_by_acl": by_acl,
        "filtered_by_status": by_status}})
    # Context: labeled passages, budgeted (Chapters 10, 17).
    labels = {c[0]: c[2] for c in cands[:6]}
    context = "\n".join(f"<SOURCE id={k}>{v}</SOURCE>"
                        for k, v in labels.items())
    prompt = (f"{INSTRUCTIONS}\n{context}\n\n"
              f"Return JSON with fields answer, "
              f'"citations", supported, confidence, escalate.\n'
              f"Q: {question}")
    # Gateway with fallback (Chapter 9); validation with bounded
    # repair (Chapters 12, 17).
    for attempt in range(2):
        try:
            raw = stub_model(prompt)
            obj = json.loads(raw)
        except json.JSONDecodeError:
            obj = None
        problems = []
        if not obj or set(obj) != {"answer", "citations",
                                   "supported", "confidence",
                                   "escalate"}:
            problems.append("schema")
        elif any(c not in labels for c in obj["citations"]):
            problems.append("citation not in context")
        elif obj["supported"] and not obj["citations"]:
            problems.append("unsupported")
        trace["spans"].append({"validation": {
            "attempt": attempt, "problems": problems}})
        if not problems:
            break
        prompt += ("\n\nValid citation labels: "
                   + ", ".join(labels))
    else:
        # Chapter 36.
        obj = {"answer": "", "citations": [], "supported": False,
               "confidence": "low", "escalate": True}
    outcome = "escalated" if obj["escalate"] else "answered"
    trace["spans"].append({"outcome": outcome})
    return {"answer": obj, "trace": trace}


if __name__ == "__main__":
    q = "How much unused leave can I carry over?"
    print("v0.1:", prototype(q))
    r = production(q, groups={"all-staff"})
    print("v1.0:", r["answer"]["answer"],
          "| cites", r["answer"]["citations"])
    print("      trace:", json.dumps(r["trace"]))
    r2 = production("What is the grade D salary band?",
                    groups={"all-staff"})
    print("v1.0 (restricted):",
          r2["trace"]["spans"][-1]["outcome"],
          "|", r2["trace"]["spans"][0]["retrieval"])
