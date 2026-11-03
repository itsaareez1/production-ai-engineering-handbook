"""Listing 11.1. Instructions as versioned artifacts with a
regression check.

Chapter 11, Instruction Design. Verified by execution with a
stubbed evaluator.
Run with: python run.py 11.1
"""
import hashlib
import json
import pathlib

INSTRUCTIONS_DIR = pathlib.Path("instructions")


def load_instructions(name: str) -> "tuple[str, str]":
    path = INSTRUCTIONS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    version = hashlib.sha256(text.encode()).hexdigest()[:12]
    return text, version


def evaluate(instruction_text: str, eval_set: list) -> dict:
    # Stub: real evaluation calls the model per item and grades the
    # output. Here we simulate a regression: the reviewer must not
    # exclude .yaml files.
    excludes_yaml = ("configuration files" in instruction_text
                     and "except" not in instruction_text)
    misses = sum(1 for item in eval_set
                 if item["file"].endswith(".yaml") and excludes_yaml)
    return {"items": len(eval_set), "missed_findings": misses}


def test_instruction_regression(
    name: str, eval_set: list, max_missed: int = 0
):
    text, version = load_instructions(name)
    result = evaluate(text, eval_set)
    status = ("PASS" if result["missed_findings"] <= max_missed
              else "FAIL")
    print(json.dumps({"instructions": name, "version": version,
                      **result, "status": status}))
    return status == "PASS"


if __name__ == "__main__":
    INSTRUCTIONS_DIR.mkdir(exist_ok=True)
    eval_set = [
        {"file": "app/config.yaml",
         "expect": "hardcoded_credential"},
        {"file": "tests/test_auth.py", "expect": None},
    ]
    (INSTRUCTIONS_DIR / "pr_review.md").write_text(
        "Review the diff for security issues. "
        "Ignore test files and configuration files.")
    test_instruction_regression("pr_review", eval_set)
    (INSTRUCTIONS_DIR / "pr_review.md").write_text(
        "Review the diff for security issues. Ignore test files, "
        "except configuration files, which must always be checked "
        "for credentials.")
    test_instruction_regression("pr_review", eval_set)
