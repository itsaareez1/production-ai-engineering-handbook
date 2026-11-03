"""Atlas answer schema, validator, and bounded repair loop.

This is Listing 12.1 of The Production AI Engineering Handbook,
packaged as a module so that Listing 33.1 can import it. The book
prints the same code as listings/ch12/listing_12_1.py.
"""
import json

ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "citations", "supported", "confidence",
                 "escalate"],
    "properties": {
        "answer": {"type": "string", "maxLength": 2000},
        "citations": {"type": "array", "items": {"type": "string"}},
        "supported": {"type": "boolean"},
        "confidence": {"type": "string",
                       "enum": ["high", "medium", "low"]},
        "escalate": {"type": "boolean"},
    },
}


def schema_errors(obj: dict) -> list:
    errs = []
    for f in ANSWER_SCHEMA["required"]:
        if f not in obj:
            errs.append(f"missing field: {f}")
    for k in obj:
        if k not in ANSWER_SCHEMA["properties"]:
            errs.append(f"unexpected field: {k}")
    if ("confidence" in obj
            and obj["confidence"] not in ("high", "medium", "low")):
        errs.append("confidence not in enum")
    if "citations" in obj and not all(
            isinstance(c, str) for c in obj["citations"]):
        errs.append("citations must be strings")
    return errs


def semantic_errors(obj: dict, valid_sources: set) -> list:
    errs = [f"unknown citation: {c}"
            for c in obj.get("citations", [])
            if c not in valid_sources]
    if obj.get("supported") and not obj.get("citations"):
        errs.append("supported answer has no citations")
    if not obj.get("supported") and not obj.get("escalate"):
        errs.append("unsupported answer must escalate")
    return errs


def get_answer(model, prompt: str, valid_sources: set,
               max_repairs: int = 2):
    attempt, feedback = 0, ""
    while attempt <= max_repairs:
        raw = model.complete(prompt + feedback)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            feedback = (
                f"\n\nYour previous output was not valid JSON: {e}. "
                "Return only the JSON object."
            )
            attempt += 1
            continue
        errs = (schema_errors(obj)
                or semantic_errors(obj, valid_sources))
        if not errs:
            return obj, attempt
        feedback = ("\n\nYour previous output had these problems: "
                    + "; ".join(errs)
                    + f". Valid citation labels: "
                      f"{sorted(valid_sources)}.")
        attempt += 1
    return {"answer": "", "citations": [], "supported": False,
            "confidence": "low", "escalate": True}, attempt


class MisbehavingStub:
    def __init__(self):
        self.calls = 0

    def complete(self, prompt):
        self.calls += 1
        if self.calls == 1:
            return json.dumps({
                "answer": "Five days carry over.",
                "citations": ["policy/leave-v6"],
                "supported": True,
                "confidence": "high",
                "escalate": False,
            })
        return json.dumps({
            "answer": "Up to five days of unused leave may be "
                      "carried over.",
            "citations": ["policy/leave-v7"],
            "supported": True,
            "confidence": "high",
            "escalate": False,
        })
