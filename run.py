#!/usr/bin/env python3
"""Run any listing from The Production AI Engineering Handbook.

    python run.py 3.1        run one listing
    python run.py --list     list every runnable listing
    python run.py --all      run every runnable listing

See Appendix K of the book for the step-by-step version of this.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Listings that cannot be executed by run.py, with the reason the book
# gives for each. These are labeled "Reviewed for correctness" in the
# book, not "Verified by execution".
NOT_RUNNABLE = {
    "14.2": (
        "listings/ch14/listing_14_2.sql",
        "needs a PostgreSQL database with the pgvector extension. "
        "Apply it with: psql -f listings/ch14/listing_14_2.sql",
    ),
    "21.1": (
        "listings/ch21/listing_21_1.jsonc",
        "is a transcript of MCP JSON-RPC messages, not a program. "
        "Validate it with: python listings/ch21/validate_21_1.py",
    ),
    "44.1": (
        "listings/ch44/Dockerfile",
        "needs Docker. Build and start it with: "
        "docker compose build && docker compose up",
    ),
}


def discover() -> dict[str, Path]:
    """Map listing number -> path, by scanning listings/chNN/."""
    found: dict[str, Path] = {}
    for path in sorted((ROOT / "listings").glob("ch*/listing_*.py")):
        parts = path.stem.split("_")  # listing, N, M
        if len(parts) != 3:
            continue
        found[f"{parts[1]}.{parts[2]}"] = path
    return found


def sort_key(number: str) -> tuple[int, int]:
    chapter, index = number.split(".")
    return int(chapter), int(index)


def run_one(number: str, path: Path, quiet: bool = False) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    print(f"--- Listing {number}  ({rel}) ---", flush=True)
    # Listing 33.1 imports atlas/validation.py, so the repository
    # root has to be importable whatever directory run.py was called
    # from. This is the "no knowledge of the folder layout is needed"
    # promise of Appendix K.
    env = dict(os.environ)
    env["PYTHONPATH"] = (
        str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    ).rstrip(os.pathsep)
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    if not quiet:
        sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout if quiet else "")
        sys.stderr.write(proc.stderr)
        print(f"FAILED: listing {number} exited with {proc.returncode}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("listing", nargs="?",
                        help="listing number, e.g. 3.1")
    parser.add_argument("--list", action="store_true", dest="do_list")
    parser.add_argument("--all", action="store_true", dest="do_all")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    runnable = discover()

    if args.do_list:
        print(f"{len(runnable)} runnable listings:")
        for number in sorted(runnable, key=sort_key):
            print(f"  {number:<6} {runnable[number].relative_to(ROOT)}")
        print()
        print(f"{len(NOT_RUNNABLE)} listings are not run by run.py:")
        for number in sorted(NOT_RUNNABLE, key=sort_key):
            path, why = NOT_RUNNABLE[number]
            print(f"  {number:<6} {path}")
            print(f"         {why}")
        return 0

    if args.do_all:
        started = time.perf_counter()
        failures = []
        for number in sorted(runnable, key=sort_key):
            if not run_one(number, runnable[number], quiet=args.quiet):
                failures.append(number)
            print()
        elapsed = time.perf_counter() - started
        print(f"{len(runnable)} listings in {elapsed:.1f}s")
        if failures:
            print(f"RESULT: {len(failures)} listing(s) failed: "
                  f"{', '.join(failures)}")
            return 1
        print("RESULT: all listings ran successfully")
        return 0

    if not args.listing:
        parser.print_help()
        return 2

    number = args.listing
    if number in NOT_RUNNABLE:
        path, why = NOT_RUNNABLE[number]
        print(f"Listing {number} ({path}) {why}")
        return 0
    if number not in runnable:
        print(f"No listing {number}. Try: python run.py --list")
        return 1
    return 0 if run_one(number, runnable[number]) else 1


if __name__ == "__main__":
    sys.exit(main())
