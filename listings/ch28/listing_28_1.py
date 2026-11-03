"""Listing 28.1. Tool registry with permission levels and a policy
layer returning allow, approval-required, or refuse.

Chapter 28, The Agent Permission Model. Verified by execution.
Run with: python run.py 28.1
"""
from dataclasses import dataclass

LEVELS = ["P0", "P1", "P2", "P3", "P4"]


@dataclass(frozen=True)
class Tool:
    name: str
    level: str
    description: str


REGISTRY = {  # per agent, per deployment; the model sees only these
    "atlas-support": [
        Tool("retrieve", "P0",
             "search approved documents the user may read"),
        Tool("lookup_ticket", "P1",
             "read a ticket the user may view"),
        Tool("draft_ticket", "P2",
             "prepare a ticket draft for confirmation"),
    ],
}
AGENT_MAX_LEVEL = {"atlas-support": "P2"}
USER_ROLES = {"alice": {"employee"},
              "sam": {"employee", "support"}}
TOOL_ROLE_REQUIREMENTS = {"lookup_ticket": {"employee"},
                          "draft_ticket": {"employee"}}


def rank(level):
    return LEVELS.index(level)


def policy(agent: str, user: str, tool_name: str, args: dict):
    tools = {t.name: t for t in REGISTRY.get(agent, [])}
    if tool_name not in tools:
        return "refuse", "tool not in registry for this agent"
    tool = tools[tool_name]
    if rank(tool.level) > rank(AGENT_MAX_LEVEL[agent]):
        return "refuse", f"tool level {tool.level} exceeds agent max"
    need = TOOL_ROLE_REQUIREMENTS.get(tool_name, set())
    if not need <= USER_ROLES.get(user, set()):
        return "refuse", "user lacks required role"
    if tool.level in ("P2", "P3", "P4"):
        return "approval", f"{tool.level} action requires confirmation"
    return "allow", "ok"


if __name__ == "__main__":
    cases = [
        ("atlas-support", "alice", "retrieve", {}),
        ("atlas-support", "alice", "lookup_ticket",
         {"ticket_id": "T-1042"}),
        ("atlas-support", "alice", "draft_ticket",
         {"summary": "VPN"}),
        ("atlas-support", "alice", "delete_ticket",
         {"ticket_id": "T-1042"}),
        ("atlas-support", "guest", "lookup_ticket",
         {"ticket_id": "T-1042"}),
    ]
    for c in cases:
        print(f"{c[2]:14s} {c[1]:6s} ->", policy(*c))
