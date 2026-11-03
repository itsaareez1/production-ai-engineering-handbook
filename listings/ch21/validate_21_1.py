#!/usr/bin/env python3
"""Structural check for Listing 21.1.

Listing 21.1 is a transcript of MCP messages, not a program, so the
book labels it "reviewed" rather than "verified by execution". This
script makes the review mechanical: it strips the comments and the
HTTP request lines, parses every JSON object, and asserts the
properties the surrounding text claims.

It is not a conformance test against a live MCP server. It checks
that the printed messages are well-formed JSON-RPC 2.0 and carry the
fields revision 2026-07-28 requires.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

PATH = pathlib.Path(__file__).with_name("listing_21_1.jsonc")
VERSION = "2026-07-28"
META_VERSION = "io.modelcontextprotocol/protocolVersion"


def parse(text: str) -> "tuple[list[dict], list[dict]]":
    """Return (http_blocks, json_objects) from the transcript."""
    http, body, in_headers = [], [], False
    for line in text.splitlines():
        if line.startswith("//"):
            continue
        if re.match(r"^(POST|GET) ", line):
            http.append({"request": line.strip(), "headers": {}})
            in_headers = True
            continue
        if in_headers:
            if not line.strip():
                in_headers = False
                continue
            m = re.match(r"^([A-Za-z][A-Za-z0-9-]*): (.+)$", line)
            if m:
                http[-1]["headers"][m.group(1)] = m.group(2).strip()
                continue
            in_headers = False
        body.append(line)

    objects, depth, buf = [], 0, []
    for line in body:
        if not line.strip() and depth == 0:
            continue
        buf.append(line)
        depth += line.count("{") - line.count("}")
        if depth == 0 and buf:
            blob = "\n".join(buf).strip()
            buf = []
            if not blob.startswith("{"):
                continue
            # The transcript wraps one long string across lines, the
            # way Python would; join those before parsing.
            blob = re.sub(r'"\s*\n\s*"', "", blob)
            objects.append(json.loads(blob))
    return http, objects


def main() -> int:
    http, objects = parse(PATH.read_text(encoding="utf-8"))
    checks: "list[tuple[str, bool]]" = []

    def check(label: str, ok: bool) -> None:
        checks.append((label, bool(ok)))

    check("transcript parses as JSON-RPC", len(objects) == 4)
    check("two HTTP request blocks", len(http) == 2)

    for block in http:
        got = block["headers"].get("MCP-Protocol-Version")
        check(f"{block['request']} carries MCP-Protocol-Version",
              got == VERSION)
        check(f"{block['request']} carries Mcp-Method",
              "Mcp-Method" in block["headers"])

    requests = [o for o in objects if "method" in o]
    results = [o for o in objects if "result" in o]
    check("two requests and two results",
          len(requests) == 2 and len(results) == 2)

    for req in requests:
        name = req["method"]
        check(f"{name} is jsonrpc 2.0", req.get("jsonrpc") == "2.0")
        meta = req.get("params", {}).get("_meta", {})
        check(f"{name} _meta states the protocol version",
              meta.get(META_VERSION) == VERSION)

    for req, hdr in zip(requests, http):
        check(f"{req['method']} header matches _meta version",
              hdr["headers"]["MCP-Protocol-Version"]
              == req["params"]["_meta"][META_VERSION])
        check(f"{req['method']} header matches method",
              hdr["headers"]["Mcp-Method"] == req["method"])

    for res in results:
        check(f"result id={res['id']} is marked complete",
              res["result"].get("resultType") == "complete")

    listing = results[0]["result"]
    check("tools/list returns one tool",
          len(listing["tools"]) == 1)
    check("the tool declares an input schema",
          listing["tools"][0]["inputSchema"]["type"] == "object")
    check("the tool list is cacheable",
          isinstance(listing.get("ttlMs"), int)
          and listing.get("cacheScope") in ("public", "session"))

    call = results[1]["result"]
    check("tools/call result is not an error",
          call["isError"] is False)
    payload = json.loads(call["content"][0]["text"])
    check("tools/call result body parses",
          payload == {"status": "open", "summary": "VPN drops"})
    check("ids pair requests with results",
          [r["id"] for r in requests] == [r["id"] for r in results])

    width = max(len(label) for label, _ in checks)
    for label, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'}  {label:<{width}}")
    failed = [label for label, ok in checks if not ok]
    print()
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print("FAILED:", "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
