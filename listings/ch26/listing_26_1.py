"""Listing 26.1. A bounded agent with separated planner, executor,
verifier, state, and budget.

Chapter 26, Agent Architecture.
Verified by execution with stubbed model calls.
Run with: python run.py 26.1
"""
from dataclasses import dataclass, field


@dataclass
class Budget:
    max_steps: int = 6
    max_tokens: int = 8000
    steps: int = 0
    tokens: int = 0

    def allow(self):
        return (self.steps < self.max_steps
                and self.tokens < self.max_tokens)

    def charge(self, tokens):
        self.steps += 1
        self.tokens += tokens


@dataclass
class State:
    goal: str
    # each entry is {action, args, result}
    history: list = field(default_factory=list)
    trace: list = field(default_factory=list)

    def seen(self, action, args):
        return any(h["action"] == action and h["args"] == args
                   for h in self.history)


TOOLS = {"lookup_ticket": {"level": "read"},
         "draft_ticket": {"level": "draft"}}


def executor(action, args, user):   # Chapter 19 loop, stubbed
    if action == "lookup_ticket":
        return {"found": args["ticket_id"] == "T-1042",
                "status": "open"}
    if action == "draft_ticket":
        return {"draft_id": "D-7", "awaiting_confirmation": True}
    return {"error": "unknown action"}


def verifier(state: State):
    """Deterministic check of the goal, independent of the planner."""
    drafts = [h for h in state.history
              if h["action"] == "draft_ticket"]
    if drafts and drafts[-1]["result"].get("awaiting_confirmation"):
        return True, "draft prepared; awaiting user confirmation"
    lookups = [h for h in state.history
               if h["action"] == "lookup_ticket"]
    if lookups and lookups[-1]["result"].get("found"):
        return True, "existing ticket located"
    return False, "goal not yet satisfied"


class StubPlanner:
    """Proposes: lookup (miss) -> lookup again (no progress) ->
    draft -> done."""

    def __init__(self):
        self.n = 0

    def propose(self, state: State) -> dict:
        self.n += 1
        plan = [
            {"action": "lookup_ticket",
             "args": {"ticket_id": "T-1099"}},
            {"action": "lookup_ticket",            # again
             "args": {"ticket_id": "T-1099"}},
            {"action": "draft_ticket",
             "args": {"summary": "VPN drops"}},
            {"action": "done", "args": {}},
        ]
        return plan[min(self.n - 1, len(plan) - 1)]


def run_agent(goal: str, user: str, planner,
              budget: Budget) -> State:
    state = State(goal)
    while budget.allow():
        proposal = planner.propose(state)
        budget.charge(tokens=600)
        action, args = proposal["action"], proposal["args"]
        state.trace.append(
            f"step {budget.steps}: propose {action} {args}")
        if action == "done":
            ok, why = verifier(state)
            state.trace.append(f"verify: {ok} ({why})")
            if ok:
                return state
            state.history.append({"action": "done", "args": {},
                                  "result": {"rejected": why}})
            continue
        if action not in TOOLS:
            state.history.append({
                "action": action, "args": args,
                "result": {"error": "no such tool"}})
            continue
        if state.seen(action, args):
            state.trace.append(
                "no-progress guard: repeated action refused")
            state.history.append({
                "action": action, "args": args,
                "result": {"error": "repeated"}})
            continue
        result = executor(action, args, user)
        state.history.append({"action": action, "args": args,
                              "result": result})
    state.trace.append("budget exhausted")
    return state


if __name__ == "__main__":
    b = Budget(max_steps=6)
    s = run_agent("resolve VPN problem via ticket", "alice",
                  StubPlanner(), b)
    print("\n".join(s.trace))
    print("outcome:", verifier(s)[1], "| steps:", b.steps,
          "| tokens:", b.tokens)
