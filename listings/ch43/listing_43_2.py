"""Listing 43.2. A threat model as data, with a completeness check.

Chapter 43, Securing AI Agents and Tools. Verified by execution.
Each component of the reference architecture is checked against the
STRIDE categories and the AI-specific classes; every applicable pair
needs a threat with controls, or an explicit "not applicable" with a
reason. The checker reports gaps and the residual risks to accept.
Run with: python run.py 43.2
"""
from dataclasses import dataclass, field

STRIDE = ("spoofing", "tampering", "repudiation", "disclosure",
          "denial", "elevation")
AI = ("injection", "agency", "poisoning", "consumption")
OWASP = {"injection": "LLM01", "agency": "LLM03",
         "poisoning": "LLM05", "consumption": "LLM06",
         "disclosure": "LLM02"}


@dataclass
class Threat:
    component: str
    category: str
    description: str
    controls: list = field(default_factory=list)  # (control, chapter)
    residual: str = "low"     # low / medium / high after controls
    owner: str = ""


@dataclass
class Component:
    name: str
    boundary: str             # trust zone the component sits in
    categories: tuple         # categories that apply to it
    not_applicable: dict = field(default_factory=dict)  # cat: reason


def check(components, threats):
    gaps, accept = [], []
    for c in components:
        for cat in c.categories:
            ts = [t for t in threats
                  if t.component == c.name and t.category == cat]
            if not ts and cat not in c.not_applicable:
                gaps.append(f"{c.name}: no threat recorded for {cat}")
            for t in ts:
                if not t.controls:
                    gaps.append(f"{c.name}/{cat}: no control")
                if t.residual != "low":
                    who = t.owner or "UNOWNED"
                    accept.append(f"{c.name}/{cat} residual "
                                  f"{t.residual} -> {who}")
    return gaps, accept


ATLAS = [
    Component("retrieval", "internal", ("disclosure", "poisoning",
                                        "injection", "tampering")),
    Component("tool executor", "internal",
              ("elevation", "agency", "repudiation", "spoofing")),
    Component("gateway", "internal", ("consumption", "denial",
                                      "disclosure"),
              {"disclosure": "holds no business data (Ch. 9)"}),
    Component("ingestion", "privileged",
              ("poisoning", "tampering", "elevation")),
]
THREATS = [
    Threat("retrieval", "disclosure", "restricted chunk returned",
           [("ACL predicate in the query", "16"),
            ("identity object only", "42")]),
    Threat("retrieval", "poisoning", "instructions in a wiki page",
           [("ingestion scan + quarantine", "40"),
            ("origin labels", "10")], "medium", "security owner"),
    Threat("retrieval", "injection", "retrieved text obeyed",
           [("containment layers", "39")], "medium",
           "security owner"),
    Threat("retrieval", "tampering", "index edited directly",
           [("index is derived; rebuild from source", "18")]),
    Threat("tool executor", "elevation", "call beyond user rights",
           [("policy layer", "28"), ("delegated token", "42")]),
    Threat("tool executor", "agency", "write without approval",
           [("P2 approval gate", "29")]),
    Threat("tool executor", "repudiation", "no record of who acted",
           [("append-only action audit", "43")]),
    Threat("tool executor", "spoofing", "forged approval",
           [("approval bound to proposal hash", "29")]),
    Threat("gateway", "consumption", "runaway token spend",
           [("budgets and caps", "46"), ("loop bounds", "26")]),
    Threat("gateway", "denial", "provider outage",
           [("fallback chain + breaker", "9")]),
    Threat("ingestion", "poisoning", "malicious document indexed",
           [("trust tiers", "40")]),
    Threat("ingestion", "elevation", "pipeline credential misused"),
]

if __name__ == "__main__":
    gaps, accept = check(ATLAS, THREATS)
    pairs = sum(len(c.categories) for c in ATLAS)
    print(f"{len(ATLAS)} components, {pairs} component-category "
          f"pairs, {len(THREATS)} threats")
    print("gaps:")
    for g in gaps:
        print("  -", g)
    print("residual risks to accept:")
    for a in accept:
        print("  -", a)
    t = THREATS[1]
    print(f"OWASP mapping for {t.category}: {OWASP[t.category]}")
