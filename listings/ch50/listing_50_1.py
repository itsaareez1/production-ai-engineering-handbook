"""Listing 50.1. Architecture fitness function: dependency rules
between modules checked against an import graph.

Chapter 50, Maintainability. Verified by execution.
Run with: python run.py 50.1
"""

RULES = {
    # module -> modules it may import from, besides the standard
    # library and itself
    "atlas.gateway": {"atlas.config", "atlas.trace"},
    "atlas.retrieval": {"atlas.config", "atlas.trace",
                        "atlas.identity"},
    "atlas.context": {"atlas.config", "atlas.trace",
                      "atlas.retrieval"},
    "atlas.validation": {"atlas.config", "atlas.schema"},
    "atlas.tools": {"atlas.config", "atlas.trace",
                    "atlas.identity", "atlas.policy"},
    "atlas.agent": {"atlas.config", "atlas.trace", "atlas.tools",
                    "atlas.policy", "atlas.gateway",
                    "atlas.validation"},
    "atlas.orchestration": {"atlas.config", "atlas.trace",
                            "atlas.retrieval", "atlas.context",
                            "atlas.gateway", "atlas.validation",
                            "atlas.tools", "atlas.agent",
                            "atlas.identity"},
    "atlas.eval": {"atlas.config", "atlas.gateway",
                   "atlas.schema"},
    "atlas.api": {"atlas.config", "atlas.orchestration",
                  "atlas.identity", "atlas.trace"},
}
FORBIDDEN_EVERYWHERE = {"providers.openai_sdk",
                        "providers.anthropic_sdk"}
ALLOWED_TO_IMPORT_PROVIDERS = {"atlas.gateway"}


def check(imports: dict) -> list:
    """imports: module -> set of imported modules (from static
    analysis)."""
    violations = []
    for mod, deps in imports.items():
        for dep in deps:
            if (dep in FORBIDDEN_EVERYWHERE
                    and mod not in ALLOWED_TO_IMPORT_PROVIDERS):
                violations.append(
                    f"{mod} imports provider SDK {dep}")
            elif dep.startswith("atlas.") and dep != mod:
                if dep not in RULES.get(mod, set()):
                    violations.append(
                        f"{mod} may not import {dep}")
    return violations


if __name__ == "__main__":
    observed = {
        "atlas.gateway": {"atlas.config", "atlas.trace",
                          "providers.openai_sdk"},
        "atlas.orchestration": {"atlas.retrieval", "atlas.gateway",
                                "atlas.validation",
                                # violation
                                "providers.anthropic_sdk"},
        "atlas.retrieval": {"atlas.identity",
                            "atlas.orchestration"},
        # calls a model
        "atlas.validation": {"atlas.schema", "atlas.gateway"},
    }
    for v in check(observed) or ["no violations"]:
        print(v)
