"""Listing 19.1. A bounded tool calling loop with validation,
authorization, and labeled results.

Chapter 19, Tool Use and Function Calling.
Verified by execution with a stubbed model.
Run with: python run.py 19.1
"""
import json
import re

TICKETS = {
    "T-1042": {"owner": "alice", "status": "open",
               "summary": "VPN drops"},
    "T-1043": {"owner": "bob", "status": "closed",
               "summary": "Badge reader"},
}

TOOLS = {
    "lookup_ticket": {
        "description": "Return status and summary of a support "
                       "ticket by id.",
        "schema": {"type": "object", "required": ["ticket_id"],
                   "properties": {"ticket_id": {"type": "string"}}},
    },
}


def validate_args(name: str, args: dict) -> list:
    schema = TOOLS[name]["schema"]
    errs = []
    for f in schema["required"]:
        if f not in args:
            errs.append(f"missing {f}")
    if name == "lookup_ticket" and "ticket_id" in args:
        if not re.fullmatch(r"T-\d{4}", str(args["ticket_id"])):
            errs.append("ticket_id must match T-NNNN")
    return errs


def authorize(user: str, name: str, args: dict) -> bool:
    if name == "lookup_ticket":
        t = TICKETS.get(args["ticket_id"])
        return t is not None and (
            t["owner"] == user or user == "support")
    return False


def execute(name: str, args: dict) -> dict:
    if name == "lookup_ticket":
        t = TICKETS[args["ticket_id"]]
        return {"status": t["status"], "summary": t["summary"]}


def run(model, user: str, question: str, max_iters: int = 4):
    messages = [{"role": "user", "content": question}]
    for i in range(max_iters):
        out = model.step(messages)
        if out["type"] == "answer":
            return out["text"], i
        name, args = out["tool"], out["args"]
        if name not in TOOLS:
            result = {"error": "unknown tool"}
        elif (errs := validate_args(name, args)):
            result = {"error": "invalid arguments: "
                               + "; ".join(errs)}
        elif not authorize(user, name, args):
            # Same message for both, so the tool cannot be used to
            # enumerate which tickets exist.
            result = {"error": "not found or not permitted"}
        else:
            result = execute(name, args)
        messages.append({
            "role": "tool", "name": name,
            "content": f"<UNTRUSTED origin=tool:{name}>"
                       + json.dumps(result)
                       + "</UNTRUSTED>",
        })
    return "I could not complete this request.", max_iters


class StubModel:
    def step(self, messages):
        last = messages[-1]
        if last["role"] == "user":
            tid = re.search(r"T-\d{4}", last["content"])
            return {"type": "tool", "tool": "lookup_ticket",
                    "args": {"ticket_id":
                             tid.group(0) if tid else "bad"}}
        return {"type": "answer", "text": "Result: " + last["content"]}


if __name__ == "__main__":
    for user, q in [("alice", "What is the status of T-1042?"),
                    ("alice", "What is the status of T-1043?"),
                    ("support", "What is the status of T-1043?")]:
        print(user, "->", run(StubModel(), user, q)[0][:90])
