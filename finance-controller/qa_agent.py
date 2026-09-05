#!/usr/bin/env python
"""Settlement Q&A agent CLI (Task 5).

Ask natural-language questions about the last reconciliation run. Every
answer is produced by an LLM with tool-call access to the audit trail and
report -- never from free-standing "knowledge" -- and is checked afterward
for any record ID that wasn't actually returned by a tool call.

Usage:
    python qa_agent.py "Why didn't INV-2026-00067 reconcile?"
    python qa_agent.py "What's our total chargeback exposure?"
    python qa_agent.py --trace "Which exceptions have no counterpart found?"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows consoles often default to a legacy codepage (cp1252) that can't
# encode Rupee signs or other characters an LLM answer may use -- reconfigure
# rather than crash on a perfectly good answer.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline.env import load_dotenv_if_present
load_dotenv_if_present()

from qa.agent import QAAgent
from qa.tools import ReconciliationStore


def main():
    parser = argparse.ArgumentParser(description="Ask a question about the last reconciliation run")
    parser.add_argument("question", type=str, help="natural-language question")
    parser.add_argument("--data-dir", type=str, default=str(ROOT / "data"))
    parser.add_argument("--output-dir", type=str, default=str(ROOT / "output"))
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--provider", type=str, default=None, choices=["anthropic", "gemini"])
    parser.add_argument("--trace", action="store_true", help="print the tool calls the agent made")
    args = parser.parse_args()

    data_dir, output_dir = Path(args.data_dir), Path(args.output_dir)
    missing = [f for f in ("report.json", "groups.json", "exceptions.json") if not (output_dir / f).exists()]
    if missing:
        print(f"Missing {missing} in {output_dir} -- run `python run_reconciliation.py` first.")
        sys.exit(1)

    store = ReconciliationStore(data_dir, output_dir)
    agent = QAAgent(store, api_key=args.api_key, provider=args.provider)
    result = agent.ask(args.question)

    print(f"\nQ: {args.question}\n")
    print(f"A: {result['answer']}\n")
    if result["provider"]:
        print(f"[provider: {result['provider']}  |  grounded: {result['grounded']}"
              + (f"  |  UNGROUNDED IDS: {result['ungrounded_ids']}" if not result["grounded"] else "") + "]")
    if args.trace:
        print("\n--- tool calls ---")
        for t in result["trace"]:
            print(f"  {t['tool']}({t['args']}) -> {str(t['result'])[:300]}")


if __name__ == "__main__":
    main()
