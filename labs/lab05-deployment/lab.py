"""Lab 5: Deploy an AI application (Chapters 44, 47, 48).

Requires Docker with Compose. Starts the stack (database, one-shot
migration, application, cache, object store), then verifies the
deployment contract: health, migrations, seeded data, quarantine,
non-root process, an authenticated request, and idempotent restart.

    python labs/lab05-deployment/lab.py          # start and verify
    python labs/lab05-deployment/lab.py --down   # stop and remove data
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://localhost:8000"


def sh(*args, check=True):
    p = subprocess.run(list(args), cwd=ROOT, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"command failed: {' '.join(args)}\n{p.stderr[-800:]}")
    return p.stdout.strip()


def http(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"content-type": "application/json",
                                          **({"authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def wait_healthy(seconds=90):
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            if http("GET", "/health") == {"status": "ok"}:
                return time.time() - t0
        except OSError:
            time.sleep(1)
    sys.exit("service did not become healthy; see: docker compose logs app")


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{': ' + detail if detail else ''}")
    return ok


if "--down" in sys.argv:
    sh("docker", "compose", "down", "-v")
    print("stack stopped; volumes removed")
    sys.exit(0)

print("== Step 1: configuration is valid")
sh("docker", "compose", "config", "--quiet")
print("  docker compose config: OK")

print("\n== Step 2: build and start")
sh("docker", "compose", "up", "-d", "--build")
print(f"  healthy after {wait_healthy():.1f}s")

print("\n== Step 3: verify the deployment contract")
ok = []
ok.append(check("migration applied", "applied" in sh("docker", "compose", "logs", "migrate")))
q = "select count(*) from documents where not quarantined"
psql = ("docker", "compose", "exec", "-T", "db", "psql", "-U", "atlas", "-d", "atlas", "-tAc")
ok.append(check("corpus seeded", sh(*psql, q) == "7"))
qq = "select doc_id from documents where quarantined"
ok.append(check("poisoned page quarantined in the database",
                sh("docker", "compose", "exec", "-T", "db", "psql", "-U", "atlas", "-d", "atlas",
                   "-tAc", qq) == "wiki-vpn"))
ok.append(check("process runs unprivileged",
                sh("docker", "compose", "exec", "-T", "app", "whoami") == "atlas"))
tok = http("POST", "/auth/dev-token", {"username": "alice"})["token"]
ans = http("POST", "/v1/ask", {"question": "How many days of unused leave can I carry over?"}, tok)
ok.append(check("authenticated question answered with a citation",
                ans["outcome"] == "answered" and bool(ans["answer"]["citations"]),
                ans["answer"]["citations"][0] if ans["answer"]["citations"] else ""))

print("\n== Step 4: restart is idempotent")
sh("docker", "compose", "restart", "app")
wait_healthy()
ok.append(check("migration re-run applies nothing",
                "nothing" in sh("docker", "compose", "run", "--rm", "migrate")))
ok.append(check("re-seeding wrote no duplicate chunks",
                sh("docker", "compose", "exec", "-T", "db", "psql", "-U", "atlas", "-d", "atlas",
                   "-tAc", "select count(*) from chunks") == "11"))
here = Path(__file__).relative_to(ROOT)
print(f"\nDeployment checks: {sum(ok)}/{len(ok)} passed. Stop with: python {here} --down")
