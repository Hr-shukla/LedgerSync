"""Settlement Q&A agent: answers natural-language questions about the
reconciliation run by giving an LLM tool-call access to qa/tools.py, never by
letting it answer from its own "knowledge" of the numbers.

Grounding is enforced two ways:
  1. The system prompt requires every factual claim to come from a tool call.
  2. After the fact, every record-id-shaped token in the final answer is
     checked against the set of ids that actually appeared in some tool
     result during the conversation -- anything else is flagged as a
     possible ungrounded reference rather than silently trusted.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .tools import TOOL_SPECS, ReconciliationStore

_ID_PATTERN = re.compile(r"\b(?:BNK\d+|STL\d+|INV-\d{4}-\d+)\b")

_SYSTEM_PROMPT = """You are a Settlement Q&A assistant for a payments reconciliation system.
You answer questions ONLY by calling the tools provided -- get_record_by_id,
get_exceptions_by_reason, get_total_value_at_risk, get_records_by_date_range,
get_match_rate_by_source. Never state a number, record id, or reason code
that did not come from a tool result. If a tool returns "found": false or an
empty list, say so plainly rather than guessing. When you give your final
answer, explicitly cite the record IDs and figures you used, so the answer
is checkable against the tool results."""

MAX_TURNS = 6


class QAAgent:
    def __init__(self, store: ReconciliationStore, api_key: str | None = None, provider: str | None = None):
        self.store = store
        self.provider = None
        self._gemini_key = None
        self._anthropic_client = None
        self._unavailable_reason = None

        import os
        anthropic_key = api_key if provider in (None, "anthropic") else None
        anthropic_key = anthropic_key or (os.environ.get("ANTHROPIC_API_KEY") if provider in (None, "anthropic") else None)
        gemini_key = api_key if provider == "gemini" else None
        gemini_key = gemini_key or (
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") if provider in (None, "gemini") else None
        )

        if anthropic_key:
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                self.provider = "anthropic"
                return
            except Exception as e:  # pragma: no cover
                self._unavailable_reason = f"anthropic client init failed: {e}"
        if gemini_key:
            self._gemini_key = gemini_key
            self.provider = "gemini"
            return
        self._unavailable_reason = self._unavailable_reason or "no ANTHROPIC_API_KEY or GEMINI_API_KEY/GOOGLE_API_KEY configured"

    @property
    def available(self) -> bool:
        return self.provider is not None

    def _dispatch(self, name: str, args: dict):
        fn = getattr(self.store, name, None)
        if fn is None:
            return {"error": f"unknown tool {name}"}
        try:
            return fn(**args)
        except TypeError as e:
            return {"error": f"bad arguments for {name}: {e}"}

    def ask(self, question: str) -> dict:
        if not self.available:
            return {
                "answer": f"Q&A agent unavailable: {self._unavailable_reason}. "
                          "Set ANTHROPIC_API_KEY or GEMINI_API_KEY/GOOGLE_API_KEY to enable it.",
                "trace": [], "grounded": None, "provider": None,
            }
        trace = []
        if self.provider == "gemini":
            answer = self._ask_gemini(question, trace)
        else:
            answer = self._ask_anthropic(question, trace)

        seen_blob = json.dumps([t["result"] for t in trace])
        seen_ids = set(_ID_PATTERN.findall(seen_blob))
        cited_ids = set(_ID_PATTERN.findall(answer))
        ungrounded = sorted(cited_ids - seen_ids)
        return {
            "answer": answer, "trace": trace, "provider": self.provider,
            "grounded": len(ungrounded) == 0, "ungrounded_ids": ungrounded,
        }

    # ------------------------------------------------------------------
    def _ask_gemini(self, question: str, trace: list) -> str:
        import requests
        function_declarations = [
            {
                "name": t["name"], "description": t["description"],
                "parameters": {"type": "OBJECT", "properties": {
                    k: {"type": "STRING", "description": v.get("description", "")} for k, v in t["params"].items()
                }, "required": t.get("required", [])},
            }
            for t in TOOL_SPECS
        ]
        contents = [
            {"role": "user", "parts": [{"text": _SYSTEM_PROMPT + "\n\nQuestion: " + question}]},
        ]
        model = "gemini-flash-lite-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {"x-goog-api-key": self._gemini_key, "Content-Type": "application/json"}

        for _ in range(MAX_TURNS):
            payload = {"contents": contents, "tools": [{"functionDeclarations": function_declarations}]}
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            contents.append({"role": "model", "parts": parts})

            calls = [p["functionCall"] for p in parts if "functionCall" in p]
            if not calls:
                return "".join(p.get("text", "") for p in parts).strip()

            response_parts = []
            for fc in calls:
                name, args = fc["name"], fc.get("args", {}) or {}
                result = self._dispatch(name, args)
                trace.append({"tool": name, "args": args, "result": result})
                response_parts.append({"functionResponse": {"name": name, "response": {"result": result}}})
            contents.append({"role": "user", "parts": response_parts})

        return "Could not produce a grounded answer within the tool-call turn limit."

    def _ask_anthropic(self, question: str, trace: list) -> str:
        anthropic_tools = [
            {
                "name": t["name"], "description": t["description"],
                "input_schema": {
                    "type": "object",
                    "properties": {k: {"type": "string", "description": v.get("description", "")} for k, v in t["params"].items()},
                    "required": t.get("required", []),
                },
            }
            for t in TOOL_SPECS
        ]
        messages = [{"role": "user", "content": question}]
        for _ in range(MAX_TURNS):
            resp = self._anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929", max_tokens=1024, system=_SYSTEM_PROMPT,
                tools=anthropic_tools, messages=messages,
            )
            messages.append({"role": "assistant", "content": resp.content})
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                return "".join(b.text for b in resp.content if b.type == "text").strip()
            tool_results = []
            for block in tool_uses:
                result = self._dispatch(block.name, block.input)
                trace.append({"tool": block.name, "args": block.input, "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
            messages.append({"role": "user", "content": tool_results})
        return "Could not produce a grounded answer within the tool-call turn limit."
