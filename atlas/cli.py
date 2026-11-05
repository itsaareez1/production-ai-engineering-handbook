"""Command line for the Atlas reference implementation.

    python -m atlas.cli ingest examples/corpus
    python -m atlas.cli ask --user alice "How many days of unused leave can I carry over?"
    python -m atlas.cli eval examples/evaluation/golden_set.jsonl
    python -m atlas.cli agent --user alice "My laptop will not boot, see T-1042"

With ATLAS_DATABASE_URL unset, each command runs against an in-memory
store seeded from examples/corpus, so it works on a fresh clone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from atlas.core.config import Settings
from atlas.core.identity import DIRECTORY
from atlas.corpus import load_corpus
from atlas.evaluation.harness import calibrate_judge, load_golden, run
from atlas.gateway.gateway import ModelRequest
from atlas.service import Atlas

CORPUS = Path(__file__).resolve().parents[1] / "examples" / "corpus"


def _service(seed: bool = True) -> Atlas:
    settings = Settings.from_env()
    svc = Atlas(settings)
    if seed and not settings.database_url:
        for d in load_corpus(CORPUS):
            svc.ingest(d)
    return svc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="atlas")
    sub = p.add_subparsers(dest="cmd", required=True)
    s_in = sub.add_parser("ingest")
    s_in.add_argument("directory")
    s_ask = sub.add_parser("ask")
    s_ask.add_argument("--user", default="alice", choices=sorted(DIRECTORY))
    s_ask.add_argument("question")
    s_ev = sub.add_parser("eval")
    s_ev.add_argument("golden")
    s_ev.add_argument("--out", default=None)
    s_ag = sub.add_parser("agent")
    s_ag.add_argument("--user", default="alice", choices=sorted(DIRECTORY))
    s_ag.add_argument("request")
    a = p.parse_args(argv)

    if a.cmd == "ingest":
        svc = _service(seed=False)
        for d in load_corpus(Path(a.directory)):
            r = svc.ingest(d)
            print(f"{r.doc_id:<18} {r.outcome:<12} chunks={r.chunks} {', '.join(r.reasons)}")
        return 0
    svc = _service()
    if a.cmd == "ask":
        r = svc.ask(a.question, DIRECTORY[a.user])
        print(json.dumps({"outcome": r.outcome, **r.answer, "trace_id": r.trace_id,
                          "cost_usd": r.cost_usd}, indent=2))
        return 0
    if a.cmd == "agent":
        out = svc.agent.run(DIRECTORY[a.user], a.request)
        print(json.dumps({"status": out.status, "summary": out.summary,
                          "approval_id": out.approval_id, "steps": out.steps}, indent=2))
        return 0
    if a.cmd == "eval":
        items, version = load_golden(Path(a.golden))
        res = run(items, svc.ask, version, svc.versions())

        def judge(item, answer) -> int:
            r = svc.gateway.complete(ModelRequest(task="judge", system="Grade the answer.",
                                                  user=json.dumps({
                                                      "answer": answer.get("answer", ""),
                                                      "must_contain_facts": list(item.must_contain_facts)})),
                                     DIRECTORY[item.user])
            ok = json.loads(r.response.text)["correct"]
            esc = bool(answer.get("escalate")) or not answer.get("supported")
            return int(ok and esc == item.must_escalate)

        cal = calibrate_judge(items, res, judge)
        report = {"golden_version": version, "system": res.system_versions,
                  "overall": res.overall(), "by_category": res.by_category(),
                  "judge_calibration": cal,
                  "failed": {k: v["grades"] for k, v in res.per_item.items()
                             if not v["grades"]["pass"]}}
        text = json.dumps(report, indent=2)
        if a.out:
            Path(a.out).write_text(text)
            json.dump({k: v for k, v in res.per_item.items()}, open(a.out + ".items.json", "w"),
                      indent=2)
        print(text)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
