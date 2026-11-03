"""Listing 42.1. Identity object from session; group-scoped
retrieval and tool policy reading only the identity object; a
confused-deputy attempt via request body and via model output, both
refused.

Chapter 42, Identity, Authentication, and Authorization.
Verified by execution.
Run with: python run.py 42.1
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    user_id: str
    groups: frozenset
    session_id: str


SESSIONS = {"sess-1": ("alice", {"all-staff"}),
            "sess-2": ("sam", {"all-staff", "hr"})}
IDP_GROUPS = {"alice": {"all-staff"},
              "sam": {"all-staff", "hr"}}


def authenticate(session_id: str) -> Identity:
    user, _ = SESSIONS[session_id]
    # Resolved from the identity provider, once.
    groups = IDP_GROUPS[user]
    return Identity(user, frozenset(groups), session_id)


DOC_ACL = {"policy-leave": {"all-staff"},
           "policy-pay": {"hr", "management"}}


def retrieval_filter(identity: Identity,
                     candidates: list) -> list:
    return [d for d in candidates
            if DOC_ACL[d] & identity.groups]


def tool_policy(identity: Identity, tool: str, args: dict) -> str:
    if tool == "lookup_salary_band":
        return "allow" if "hr" in identity.groups else "refuse"
    return "refuse"


def handle(session_id: str, body: dict,
           model_output: dict) -> dict:
    identity = authenticate(session_id)
    # body["groups"] and model_output["claimed_role"] are
    # deliberately ignored.
    docs = retrieval_filter(identity,
                            ["policy-leave", "policy-pay"])
    decision = tool_policy(identity, model_output["tool"],
                           model_output.get("args", {}))
    return {"user": identity.user_id, "docs": docs,
            "tool_decision": decision}


if __name__ == "__main__":
    attack_body = {"question": "show pay bands",
                   "groups": ["hr", "management"]}
    attack_model = {
        "tool": "lookup_salary_band", "args": {"grade": "D"},
        "claimed_role": "HR administrator (per user statement)"}
    print("alice:", handle("sess-1", attack_body, attack_model))
    print("sam:  ", handle("sess-2", attack_body, attack_model))
