"""Provider adapters.

`MockProvider` is deterministic and offline. It is what the tests, the
labs, and a fresh clone use, so nothing in this repository needs a paid
account. It answers by quoting the best-matching sentence from the
labeled sources it is given, plans agent steps with simple rules, and
judges answers against reference facts. Faults (errors, bad citations,
unsupported claims) can be injected to exercise every control path.

`AnthropicProvider` and `OpenAIProvider` call real APIs through the
official SDKs. They are **not exercised by the test suite**; enabling
them requires `pip install -r requirements-providers.txt`, an API key in
the environment (ANTHROPIC_API_KEY / OPENAI_API_KEY), and
ATLAS_MODEL_PROVIDER=anthropic|openai. Parameter names follow the
providers' structured-output documentation as checked for the book; see
Chapter 12 and confirm against the current documentation.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from atlas.gateway.gateway import ModelRequest, ModelResponse, ProviderError
from atlas.retrieval.text import approx_tokens, words

_SOURCE = re.compile(r'<SOURCE label="([^"]+)"[^>]*>\n(.*?)\n</SOURCE>', re.S)
_TICKET = re.compile(r"\bT-\d{4}\b")


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip(" -*|") for p in parts if len(p.strip()) > 12]


@dataclass
class MockProvider:
    name: str = "mock"
    in_region: bool = True
    fail_next: int = 0                 # raise transient errors for N calls
    permanent_failure: bool = False
    faults: list[str] = field(default_factory=list)  # consumed in order
    stubborn_planner: bool = False     # repeats an action (no-progress test)
    calls: int = 0

    def complete(self, model: str, req: ModelRequest, timeout_s: float) -> ModelResponse:
        self.calls += 1
        t0 = time.perf_counter()
        if self.permanent_failure:
            raise ProviderError("400 invalid request", transient=False)
        if self.fail_next > 0:
            self.fail_next -= 1
            raise ProviderError("503 overloaded", transient=True)
        fault = self.faults.pop(0) if self.faults else None
        if req.task == "answer":
            text = self._answer(req.user, fault)
        elif req.task == "plan":
            text = self._plan(req.user)
        elif req.task == "judge":
            text = self._judge(req.user)
        else:
            raise ProviderError(f"unknown task {req.task}", transient=False)
        return ModelResponse(text, approx_tokens(req.system + req.user), approx_tokens(text),
                             model, self.name, (time.perf_counter() - t0) * 1000)

    # --- answer: quote the best-supported sentence and cite its label
    def _answer(self, prompt: str, fault: str | None) -> str:
        question = prompt.rsplit("QUESTION:", 1)[-1].strip().splitlines()[0]
        q = set(words(question))
        best = (0.0, "", "")
        for label, text in _SOURCE.findall(prompt):
            for s in _sentences(text):
                sw = set(words(s))
                score = len(q & sw) / (len(q) or 1)
                if score > best[0]:
                    best = (score, s, label)
        score, sentence, label = best
        if fault == "bad_citation":
            return json.dumps({"answer": sentence or "Ten days.", "citations": ["policy/ghost#0"],
                               "supported": True, "confidence": "high", "escalate": False})
        if fault == "unsupported_claim":
            return json.dumps({"answer": (sentence + " Contractors are excluded.").strip(),
                               "citations": [label] if label else [], "supported": True,
                               "confidence": "high", "escalate": False})
        if fault == "not_json":
            return "Sure! The answer is five days."
        if score < 0.5 or not sentence:
            return json.dumps({"answer": "I could not find this in the sources I can access.",
                               "citations": [], "supported": False, "confidence": "low",
                               "escalate": True})
        return json.dumps({"answer": sentence, "citations": [label], "supported": True,
                           "confidence": "high" if score >= 0.75 else "medium",
                           "escalate": False})

    # --- plan: the agent planner (Chapter 26)
    def _plan(self, prompt: str) -> str:
        state = json.loads(prompt)
        history = state.get("history", [])
        done = {h["action"] for h in history}
        ids = _TICKET.findall(state.get("request", ""))
        if self.stubborn_planner and ids:
            return json.dumps({"action": "lookup_ticket", "args": {"ticket_id": ids[0]}})
        if ids and "lookup_ticket" not in done:
            return json.dumps({"action": "lookup_ticket", "args": {"ticket_id": ids[0]}})
        last = history[-1] if history else {}
        if last.get("action") == "lookup_ticket" and last.get("ok"):
            return json.dumps({"action": "done", "args": {"summary": last.get("result", "")}})
        if "draft_ticket" not in done:
            subject = state.get("request", "")[:80]
            return json.dumps({"action": "draft_ticket",
                               "args": {"subject": subject, "body": state.get("request", "")}})
        return json.dumps({"action": "done", "args": {"summary": "draft awaiting confirmation"}})

    # --- judge: correctness against reference facts (Chapter 35)
    def _judge(self, prompt: str) -> str:
        item = json.loads(prompt)
        answer = item.get("answer", "").lower()
        facts = item.get("must_contain_facts", [])
        return json.dumps({"correct": all(f.lower() in answer for f in facts)})


_STRICT_UNSUPPORTED = {"maxLength", "minLength", "pattern", "maximum", "minimum",
                       "maxItems", "minItems", "format"}


def strict_schema(schema: dict) -> dict:
    """The structural subset strict modes accept; Atlas's validator
    enforces the dropped limits itself (Chapter 12)."""
    if isinstance(schema, dict):
        return {k: strict_schema(v) for k, v in schema.items() if k not in _STRICT_UNSUPPORTED}
    if isinstance(schema, list):
        return [strict_schema(v) for v in schema]
    return schema


class AnthropicProvider:
    """Anthropic Messages API via the official SDK. Requires credentials."""

    name = "anthropic"

    def __init__(self, in_region: bool, client=None):
        import anthropic  # optional dependency

        self._mod = anthropic
        self._client = client or anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.in_region = in_region

    def complete(self, model: str, req: ModelRequest, timeout_s: float) -> ModelResponse:
        a = self._mod
        kwargs: dict = {
            "model": model,
            "max_tokens": req.max_output_tokens,
            "system": req.system,
            "messages": [{"role": "user", "content": req.user}],
            "timeout": timeout_s,
        }
        if req.schema:
            kwargs["output_config"] = {"format": {"type": "json_schema",
                                                  "schema": strict_schema(req.schema)}}
        t0 = time.perf_counter()
        try:
            msg = self._client.messages.create(**kwargs)
        except (a.RateLimitError, a.APITimeoutError, a.APIConnectionError,
                a.InternalServerError) as exc:
            raise ProviderError(str(exc), transient=True) from exc
        except a.APIStatusError as exc:
            raise ProviderError(str(exc), transient=False) from exc
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return ModelResponse(text, msg.usage.input_tokens, msg.usage.output_tokens, model,
                             self.name, (time.perf_counter() - t0) * 1000)


class OpenAIProvider:
    """OpenAI Chat Completions via the official SDK. Requires credentials."""

    name = "openai"

    def __init__(self, in_region: bool, client=None):
        import openai  # optional dependency

        self._mod = openai
        self._client = client or openai.OpenAI()  # reads OPENAI_API_KEY
        self.in_region = in_region

    def complete(self, model: str, req: ModelRequest, timeout_s: float) -> ModelResponse:
        o = self._mod
        kwargs: dict = {
            "model": model,
            "messages": [{"role": "system", "content": req.system},
                         {"role": "user", "content": req.user}],
            "max_completion_tokens": req.max_output_tokens,
            "timeout": timeout_s,
        }
        if req.schema:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": {
                "name": f"atlas_{req.task}", "schema": strict_schema(req.schema), "strict": True}}
        t0 = time.perf_counter()
        try:
            r = self._client.chat.completions.create(**kwargs)
        except (o.RateLimitError, o.APITimeoutError, o.APIConnectionError,
                o.InternalServerError) as exc:
            raise ProviderError(str(exc), transient=True) from exc
        except o.APIStatusError as exc:
            raise ProviderError(str(exc), transient=False) from exc
        text = r.choices[0].message.content or ""
        return ModelResponse(text, r.usage.prompt_tokens, r.usage.completion_tokens, model,
                             self.name, (time.perf_counter() - t0) * 1000)
