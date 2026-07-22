"""
Verifies that every prompt recommended in the demo materials actually produces a
good result against the CURRENTLY INDEXED corpus.

Run this before recording the demo video. A prompt that worked last week may not
work today if the corpus changed.

Usage:  python scripts/verify_demo_prompts.py
"""

import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000/api/v1"

# (prompt, label, expectation)
#   "answer"  -> must return citations
#   "refuse"  -> must return zero citations and zero confidence
PROMPTS = [
    ("What is the maximum discharge pressure for P-101A?", "Knowledge retrieval", "answer"),
    ("What maintenance and failure history exists for P-101A?", "Maintenance history", "answer"),
    ("What safety requirements apply to PSV-1201?", "Compliance", "answer"),
    ("Are there conflicting pressure values in the documents?", "Conflict detection", "answer"),
    ("Why did the mechanical seal on P-101A fail twice?", "Cross-document RCA", "answer"),
    ("What outstanding work remains after the May 2024 turnaround?", "Open actions", "answer"),
    ("Which procedure should be followed to change over the crude charge pumps?", "Procedure lookup", "answer"),
    ("What do the documents say about K-2101?", "Asset summary", "answer"),
    ("What is quantum computing?", "Off-domain refusal", "refuse"),
    ("Tell me a joke.", "Off-domain refusal", "refuse"),
    ("A", "Junk input refusal", "refuse"),
]


def ask(query: str) -> dict:
    request = urllib.request.Request(
        f"{API}/query/submit",
        data=json.dumps({"query": query, "routing_mode": "FALLBACK"}).encode(),
        headers={"Content-Type": "application/json", "X-IndusBrain-Role": "manager"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def main() -> None:
    print(f"\n{'PROMPT':<58} {'SCORE':>6} {'CITES':>6} {'MEM':>4}  AGENT")
    print("-" * 108)

    failures = []

    for prompt, label, expectation in PROMPTS:
        try:
            result = ask(prompt)
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"  {prompt[:56]:<56}  REQUEST FAILED: {error}")
            failures.append((label, prompt, "request failed"))
            continue

        citations = len(result.get("citations", []))
        score = result.get("confidence_score", 0.0)
        memory = len(result.get("organizational_memory", {}).get("past_actions", []))
        path = result.get("reasoning_path") or ["?"]
        agent = path[-1]

        if expectation == "answer":
            ok = citations > 0
        else:
            ok = citations == 0 and score == 0.0

        marker = " " if ok else "!"
        print(f"{marker} {prompt[:56]:<56} {score:>6.1f} {citations:>6} {memory:>4}  {agent}")

        if not ok:
            failures.append((label, prompt, f"expected {expectation}"))

    print("-" * 108)
    if failures:
        print(f"\n{len(failures)} PROMPT(S) NEED ATTENTION:\n")
        for label, prompt, reason in failures:
            print(f"  [{label}] {prompt}\n      -> {reason}")
        sys.exit(1)

    print(f"\nAll {len(PROMPTS)} demo prompts behave as expected.\n")


if __name__ == "__main__":
    main()
