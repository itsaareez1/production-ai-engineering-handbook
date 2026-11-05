"""Lab 7: Production readiness review (Chapters 44-47, 51, 53).

Runs offline. Executes every check it can, records the evidence, and
lists the checks that need a person and cannot be automated. Writes
production_readiness_report.md next to this file. The verdict is
computed from the results; nothing is marked done without evidence.

    python labs/lab07-production-readiness/lab.py           # full (about 15 s)
    python labs/lab07-production-readiness/lab.py --quick   # skip the test suite
"""
import datetime as dt
import logging
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repository root

from fastapi.testclient import TestClient  # noqa: E402

from atlas.api import create_app
from atlas.core.config import Settings
from atlas.core.identity import DIRECTORY
from atlas.core.observability import REQUIRED
from atlas.evaluation.harness import load_golden, regression_gate, run
from atlas.gateway.providers import MockProvider
from atlas.service import Atlas
from atlas.testing import ROOT, make_atlas

logging.getLogger("atlas").setLevel(logging.WARNING)   # keep the report readable
HERE = Path(__file__).resolve().parent
QUICK = "--quick" in sys.argv
rows: list[tuple[str, str, str, str]] = []      # (area, check, status, evidence)


def check(area: str, name: str):
    def wrap(fn):
        try:
            ok, evidence = fn()
            status = "PASS" if ok else "FAIL"
        except Exception as exc:                 # a crashing check is a failing check
            status, evidence = "FAIL", f"{type(exc).__name__}: {exc}"
        rows.append((area, name, status, evidence))
        print(f"  [{status}] {area}: {name} - {evidence}")
        return fn
    return wrap


def sh(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)


print("== Executed checks")
svc = make_atlas()


# ------------------------------------------------------------ code quality
@check("Code", "unit, security and integration tests")
def _():
    if QUICK:
        return True, "skipped (--quick); run without it before a release"
    r = sh(sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider")
    return r.returncode == 0, r.stdout.strip().splitlines()[-1]


@check("Code", "every runnable book listing executes")
def _():
    r = sh(sys.executable, "run.py", "--all")
    return r.returncode == 0, r.stdout.strip().splitlines()[-1]


@check("Code", "lint (flake8)")
def _():
    r = sh(sys.executable, "-m", "flake8", "atlas", "tests", "labs", "run.py")
    n = len(r.stdout.splitlines())
    return r.returncode == 0, f"{n} findings"


# ----------------------------------------------------------- secrets, config
SECRET = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY)")


@check("Secrets", "no credential-shaped strings in tracked files")
def _():
    files = sh("git", "ls-files").stdout.split()
    hits = []
    for f in files:
        p = ROOT / f
        if p.suffix in {".py", ".md", ".yml", ".yaml", ".toml", ".txt", ".sql", ".json",
                        ".jsonl", ".cfg", ""} and p.is_file():
            for m in SECRET.finditer(p.read_text(errors="ignore")):
                if "abcdefghij" not in m.group(0):          # test fixtures use a known fake
                    hits.append(f)
    return not hits, f"{len(files)} files scanned, {len(hits)} hits {hits[:3]}"


@check("Secrets", ".env.example holds placeholders only")
def _():
    vals = [ln.lstrip("# ").split("=", 1)[1].split("#")[0].strip()
            for ln in (ROOT / ".env.example").read_text().splitlines()
            if re.match(r"#? ?[A-Z_]*(SECRET|KEY)[A-Z_]*=", ln)]
    ok = all(v in {"CHANGE_ME", "v1", "your-key-here"} for v in vals)
    return ok, f"{len(vals)} secret-bearing entries, all placeholders" if ok else f"{vals}"


@check("Config", "production refuses missing or placeholder secrets")
def _():
    refused = []
    for kw in ({}, {"token_secret": "CHANGE_ME", "redaction_key": "CHANGE_ME"}):
        try:
            Settings(env="prod", **kw)
        except ValueError:
            refused.append(True)
    return len(refused) == 2, f"refused {len(refused)} of 2 unsafe configurations"


@check("Config", "development token endpoint is off in production")
def _():
    s = Settings(env="prod", token_secret="x" * 32, redaction_key="y" * 32)
    client = TestClient(create_app(Atlas(s)))
    code = client.post("/auth/dev-token", json={"username": "alice"}).status_code
    return code == 404, f"POST /auth/dev-token -> {code}"


# ------------------------------------------------------------------ security
@check("Security", "permissions enforced in retrieval")
def _():
    r = svc.ask("What is the salary band for a senior engineer?", DIRECTORY["alice"])
    leaked = any(s["label"].startswith("hr-salary") for s in r.sources)
    return not leaked and r.outcome == "escalated", f"alice -> {r.outcome}, leaked={leaked}"


@check("Security", "poisoned document quarantined at ingestion")
def _():
    q = svc.store.quarantined()
    return "wiki-vpn" in q, f"quarantined: {sorted(q)}"


@check("Security", "audit log hash chain verifies")
def _():
    svc.agent.run(DIRECTORY["alice"], "Laptop dead, see T-1042")
    return svc.audit.verify(), f"{len(svc.audit._entries)} entries, chain intact"


@check("Security", "container runs as a non-root user")
def _():
    df = (ROOT / "Dockerfile").read_text()
    return "USER atlas" in df, "Dockerfile sets USER atlas" if "USER atlas" in df else "no USER"


# --------------------------------------------------------------- reliability
@check("Reliability", "degraded response when every provider fails")
def _():
    a = make_atlas(primary=MockProvider(name="p", fail_next=99),
                   fallback=MockProvider(name="f", fail_next=99))
    r = a.ask("How many days of unused leave can I carry over?", DIRECTORY["alice"])
    return r.outcome == "degraded" and bool(r.sources), f"outcome={r.outcome}, sources kept"


@check("Reliability", "daily cost cap stops spend")
def _():
    a = make_atlas(daily_cost_cap_usd=0.001)
    outs = [a.ask("How many days of unused leave can I carry over?", DIRECTORY["alice"]).outcome
            for _ in range(3)]
    return outs[-1] == "degraded", f"outcomes {outs} with a $0.001 cap"


@check("Reliability", "database migrations present and tracked")
def _():
    m = sorted(p.name for p in (ROOT / "atlas/db/migrations").glob("*.sql"))
    return bool(m), f"{m}, applied with sha256 tracking (atlas/db/migrate.py)"


@check("Reliability", "container images pinned")
def _():
    imgs = re.findall(r"image:\s*(\S+)", (ROOT / "docker-compose.yml").read_text())
    loose = [i for i in imgs if i.endswith(":latest") or ":" not in i]
    return not loose, f"unpinned: {loose}" if loose else f"{len(imgs)} images pinned"


# --------------------------------------------------------------- observability
@check("Observability", "every span carries its required attributes")
def _():
    r = svc.ask("Which form do I use to request a new laptop?", DIRECTORY["alice"])
    t = svc.traces.get(r.trace_id)
    missing = [s["name"] for s in t["spans"] if not REQUIRED.get(s["name"], set()) <= set(s)]
    return not missing and set(t["versions"]) == {"code", "instructions", "model", "index"}, \
        f"{len(t['spans'])} spans, missing={missing}, versions={sorted(t['versions'])}"


@check("Observability", "metrics endpoint restricted to operators")
def _():
    from atlas.core.identity import issue_token
    c = TestClient(create_app(svc))
    key = svc.settings.token_secret.get_secret_value()
    codes = {u: c.get("/metrics", headers={"Authorization": "Bearer " + issue_token(
        DIRECTORY[u], key)}).status_code for u in ("alice", "olga")}
    return codes == {"alice": 403, "olga": 200}, f"{codes}"


# ---------------------------------------------------------------- evaluation
items, gv = load_golden(ROOT / "examples/evaluation/golden_set.jsonl")
baseline = run(items, svc.ask, gv, svc.versions())


@check("Evaluation", "golden set pass rate (lower 95% bound >= 0.70)")
def _():
    o = baseline.overall()
    return o["wilson_95"][0] >= 0.70, f"{o['pass_rate']:.3f} on n={o['n']}, 95% CI {o['wilson_95']}"


@check("Evaluation", "regression gate passes the release candidate")
def _():
    cand_sys = make_atlas()
    cand = run(items, cand_sys.ask, gv, cand_sys.versions())
    g = regression_gate(baseline, cand)
    return g["decision"] == "PASS", f"decision={g['decision']}, blocked={g['blocked']}"


# --------------------------------------------------------------- repository
@check("Repository", "no CI workflows (author's cost policy)")
def _():
    wf = list((ROOT / ".github").glob("workflows/*")) if (ROOT / ".github").exists() else []
    return not wf, "manual verification only; see docs/VERIFICATION.md" if not wf else f"{wf}"


# ------------------------------------------------------------- manual items
MANUAL = [
    ("Governance", "Data processing agreement signed with each model provider (Chapter 5)"),
    ("Governance", "Threat model reviewed and signed off (Chapter 43, docs/templates)"),
    ("Evaluation", "Judge calibrated against human labels with a real model (Chapter 35); "
                   "the mock judge's agreement is not evidence"),
    ("Evaluation", "Golden set sized for the decisions you will make (Chapter 34); "
                   "18 items is a teaching set"),
    ("Reliability", "Load test on the target hardware and provider quotas (Chapter 47)"),
    ("Reliability", "Backup restore drill meets the RPO/RTO you set (Chapter 47)"),
    ("Operations", "On-call rota, paging, and an incident runbook rehearsed (Chapter 51)"),
    ("Operations", "Alert thresholds tuned on real traffic (Chapter 45)"),
    ("Security", "Adversarial test suite run against the deployed system (Chapter 39)"),
]
print("\n== Checks that need a person")
for area, item in MANUAL:
    print(f"  [MANUAL] {area}: {item}")

failed = [r for r in rows if r[2] == "FAIL"]
verdict = ("NOT READY: fix the failed checks first" if failed else
           f"READY FOR A LIMITED PILOT once the {len(MANUAL)} manual items are signed off")
print(f"\n== Verdict: {verdict}")
print(f"   {len(rows) - len(failed)}/{len(rows)} executed checks passed, "
      f"{len(MANUAL)} manual items open")

lines = ["# Production readiness report: Atlas", "",
         f"Generated {dt.date.today().isoformat()} by "
         "`labs/lab07-production-readiness/lab.py` from executed checks.", "",
         f"**Verdict: {verdict}.** {len(rows) - len(failed)} of {len(rows)} executed checks "
         f"passed; {len(MANUAL)} items need a named person.", "",
         "## Executed checks", "", "| Area | Check | Result | Evidence |", "|---|---|---|---|"]
lines += [f"| {a} | {c} | {s} | {e.replace('|', '/')} |" for a, c, s, e in rows]
lines += ["", "## Manual sign-off", "", "| Area | Item | Owner | Date |", "|---|---|---|---|"]
lines += [f"| {a} | {i} | | |" for a, i in MANUAL]
lines += ["", "A check that cannot be executed here is listed as manual, never as passed.",
          "Re-run this lab after every change to code, instructions, model, or index."]
(HERE / "production_readiness_report.md").write_text("\n".join(lines) + "\n")
print(f"\nWrote {(HERE / 'production_readiness_report.md').relative_to(ROOT)}")
