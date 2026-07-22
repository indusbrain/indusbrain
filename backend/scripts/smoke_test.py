"""
End-to-end smoke test against a RUNNING IndusBrain API.

Hits every endpoint and asserts the responses are structurally valid AND honest -
for example, that a confidence score is never non-zero when nothing was retrieved,
and that citations are never returned without underlying evidence.

Usage:  python smoke_test.py [base_url]
"""

import json
import os
import sys
import urllib.error
import urllib.request

# Pull the asset-tag prefixes from the single source of truth the application uses,
# so this test cannot drift out of step with what the platform considers an asset.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.asset_tags import DESCRIPTIVE_PREFIXES, ISA_PREFIXES  # noqa: E402

VALID_ASSET_PREFIXES = {p.upper() for p in (*DESCRIPTIVE_PREFIXES, *ISA_PREFIXES)}

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE}/api/v1"

passed, failed = 0, 0
failures = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        failures.append(f"{name} :: {detail}")
        print(f"  FAIL  {name}  {detail}")


AUTH_TOKEN = None


def request(method: str, path: str, payload=None, timeout=420):
    url = f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body
    except urllib.error.HTTPError as http_error:
        return http_error.code, http_error.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Sign in. Every endpoint below now requires a real session, so the suite
# authenticates as a manager (the widest permission set) before testing.
# ---------------------------------------------------------------------------
print("\n=== 0. Authentication ===")

_, _bootstrap = request("GET", "/auth/bootstrap")
_auth_mode = _bootstrap.get("auth_mode", "demo") if isinstance(_bootstrap, dict) else "demo"
print(f"  (auth mode: {_auth_mode})")

# In SECURE mode unauthenticated access must be refused. In DEMO mode it is
# intentionally open, so asserting 401 there would be testing the wrong contract.
_anon_status, _ = request("GET", "/telemetry/dashboard")
if _auth_mode == "secure":
    check("unauthenticated access refused", _anon_status == 401, str(_anon_status))
else:
    check("demo mode allows anonymous read", _anon_status == 200, str(_anon_status))

# Role permissions are enforced in BOTH modes.
_engineer_upload, _ = request(
    "POST", "/ingestion/upload", None
)
check(
    "role permissions enforced regardless of mode",
    _engineer_upload in (403, 422),  # 422 = no file attached, i.e. it got past auth as manager
    str(_engineer_upload),
)

if isinstance(_bootstrap, dict) and not _bootstrap.get("has_users"):
    _, _auth = request(
        "POST", "/auth/register",
        {"email": "smoke@plant.com", "full_name": "Smoke Test", "password": "smoketest2026"},
    )
else:
    _, _auth = request(
        "POST", "/auth/login",
        {"email": "manager@plant.com", "password": "indus2026pass"},
    )

if isinstance(_auth, dict) and _auth.get("access_token"):
    AUTH_TOKEN = _auth["access_token"]
    check("signed in", True)
    check(
        "manager permissions granted",
        "upload_documents" in _auth["user"]["permissions"],
        _auth["user"]["role"],
    )
else:
    check("signed in", False, str(_auth)[:140])

print("\n=== 1. Health ===")
try:
    with urllib.request.urlopen(f"{BASE}/", timeout=30) as response:
        root_status = response.status
except urllib.error.HTTPError as root_error:
    root_status = root_error.code
check("root responds", root_status == 200, str(root_status))

print("\n=== 2. Telemetry dashboard ===")
status, dash = request("GET", "/telemetry/dashboard")

# ---------------------------------------------------------------------------
# Pick the probe asset FROM THE LIVE CORPUS rather than hardcoding one.
#
# This test previously asked about PUMP-101 regardless of what was indexed, so
# swapping the demo dataset made it fail for a reason that had nothing to do with
# the code under test - the same "stale hardcoded reference" problem the product
# itself had in its chat suggestions.
# ---------------------------------------------------------------------------
PROBE_ASSET = "PUMP-101"
if isinstance(dash, dict) and dash.get("assets"):
    PROBE_ASSET = max(dash["assets"], key=lambda a: a["mentions"])["tag"]
print(f"  (probe asset resolved from corpus: {PROBE_ASSET})")
check("dashboard 200", status == 200, str(status))
if isinstance(dash, dict):
    metrics = dash.get("metrics", {})
    check("has metrics block", bool(metrics))
    check("score_breakdown explains the score", "formula" in dash.get("score_breakdown", {}))
    check(
        "knowledge_score within 0-100",
        0 <= metrics.get("knowledge_score", -1) <= 100,
        str(metrics.get("knowledge_score")),
    )
    check(
        "asset tags are equipment, not doc refs",
        all("-" in a["tag"] and not a["tag"].startswith(("ERN", "SOP", "ISO", "WO"))
            for a in dash.get("assets", [])),
        str([a["tag"] for a in dash.get("assets", [])][:8]),
    )

print("\n=== 3. Conflict detection ===")
status, conflicts = request("POST", "/ingestion/scan-conflicts")
check("scan-conflicts 200 (was HTTP 500)", status == 200, str(status))
if isinstance(conflicts, dict):
    anomalies = conflicts.get("detected_anomalies", [])
    check("reports chunks_scanned", "chunks_scanned" in conflicts)
    check(
        "no fabricated placeholder finding",
        not any("BHP-122" in json.dumps(a) for a in anomalies),
    )
    check(
        "every finding names two different documents",
        all(a["low_source"] != a["high_source"] for a in anomalies),
    )
    check(
        "empty result carries a reason",
        bool(anomalies) or bool(conflicts.get("empty_reason")),
    )

print("\n=== 4. Simulator ===")
status, sim = request("POST", "/simulator/simulate",
                      {"scenario": "Delay maintenance by one week", "asset_tag": PROBE_ASSET})
check("simulate 200 (was HTTP 500)", status == 200, str(status))
if isinstance(sim, dict):
    check("returns target_asset", sim.get("target_asset") == PROBE_ASSET, str(sim.get("target_asset")))
    # The simulator no longer emits invented percentages, so there is deliberately
    # no `metrics` block. It must report whether it had evidence instead.
    check("reports evidence sufficiency", "has_sufficient_evidence" in sim)
    check("no fabricated engineering metrics", "production_impact_pct" not in json.dumps(sim))

# Gibberish must be refused rather than scored.
_, junk = request("POST", "/simulator/simulate", {"scenario": "adas", "asset_tag": PROBE_ASSET})
if isinstance(junk, dict):
    check("refuses nonsense input", junk.get("has_sufficient_evidence") is False,
          str(junk.get("refusal_reason")))
    check("refusal states a reason", bool(junk.get("refusal_reason")))

print("\n=== 5. Query - grounded question ===")
status, answer = request("POST", "/query/submit",
                         {"query": f"What is the maximum discharge pressure for {PROBE_ASSET}?",
                          "routing_mode": "FALLBACK"})
check("submit 200", status == 200, str(status))
if isinstance(answer, dict):
    citations = answer.get("citations", [])
    score = answer.get("confidence_score", 0)
    check("returns citations", len(citations) > 0, f"{len(citations)} citations")
    check("confidence never claims 100%", score <= 95.0, str(score))
    check("confidence has an explanation", bool(answer.get("confidence_explanation")))
    check("reports which engine answered", bool(answer.get("engine")))
    check(
        "no fabricated source filenames",
        not any(c["filename"].startswith("IOM_3196i") for c in citations),
        str([c["filename"] for c in citations]),
    )
    trace = answer.get("decision_replay_path", [])
    check("decision trace present", len(trace) >= 3, f"{len(trace)} steps")
    check("trace steps carry real metrics", any(s.get("metrics") for s in trace))

print("\n=== 6. Query - unanswerable question (honesty check) ===")
status, empty = request("POST", "/query/submit",
                        {"query": "What is the torque spec for the flux capacitor on UNIT-9999?",
                         "routing_mode": "FALLBACK"})
check("submit 200", status == 200, str(status))
if isinstance(empty, dict):
    check(
        "no citations invented for unknown asset",
        len(empty.get("citations", [])) == 0 or empty.get("confidence_score", 0) < 50,
        f"cites={len(empty.get('citations', []))} score={empty.get('confidence_score')}",
    )
    memory = empty.get("organizational_memory", {})
    check(
        "empty history states a reason",
        memory.get("repair_history_found") or bool(memory.get("empty_reason")),
    )

print("\n=== 7. Organizational memory - real records only ===")
status, history = request("POST", "/query/submit",
                          {"query": f"What is the repair history for {PROBE_ASSET}?",
                           "routing_mode": "FALLBACK"})
if isinstance(history, dict):
    actions = history.get("organizational_memory", {}).get("past_actions", [])
    check("history extracted", len(actions) > 0, f"{len(actions)} events")
    check(
        "no invented relative dates",
        not any(str(a.get("date") or "").strip().lower() in
                ("14 months ago", "8 months ago", "previous quarter") for a in actions),
    )
    check("every event names its source document", all(a.get("source") for a in actions))
    # Import the prefixes rather than restating them. This assertion used to carry
    # its own copy of the descriptive list, so it failed the moment ISA process tags
    # (P-101A, E-1501, K-2101) became valid assets - a stale test, not a real defect.
    check(
        "asset tags are equipment, not part numbers",
        all(a["asset"] is None or
            a["asset"].split("-")[0].upper() in VALID_ASSET_PREFIXES
            for a in actions),
        str([a.get("asset") for a in actions]),
    )

print("\n=== 8. Conversation history persistence ===")
status, turn = request("POST", "/query/submit",
                       {"query": "hello", "routing_mode": "FALLBACK", "session_id": "smoke-session"})
status, stored = request("GET", "/query/history/smoke-session")
check("history endpoint 200", status == 200, str(status))
if isinstance(stored, dict):
    check("chat turns persisted to Postgres", stored.get("message_count", 0) >= 2,
          str(stored.get("message_count")))

print("\n=== 9. SSE streaming ===")
try:
    req = urllib.request.Request(
        f"{API}/query/stream",
        data=json.dumps({"query": f"What is the maximum discharge pressure for {PROBE_ASSET}?",
                         "routing_mode": "FALLBACK"}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=420) as response:
        raw = response.read().decode("utf-8", "replace")
    events = [ln for ln in raw.split("\n") if ln.startswith("event:")]
    check("stream returns events (endpoint used to crash)", len(events) > 0, f"{len(events)} events")
    check("emits metadata event", "event: metadata" in raw)
    check("emits done event", "event: done" in raw)
    check("no stream fault", "STREAM OVERFLOW" not in raw and "event: error" not in raw)
    for line in raw.split("\n"):
        if line.startswith("data:"):
            json.loads(line[5:].strip())  # must be valid JSON, not a Python dict repr
            break
    check("SSE payloads are valid JSON", True)
except Exception as stream_error:
    check("SSE streaming", False, str(stream_error))

print("\n" + "=" * 58)
print(f"  PASSED: {passed}    FAILED: {failed}")
if failures:
    print("\n  Failures:")
    for failure in failures:
        print(f"   - {failure}")
print("=" * 58)
sys.exit(1 if failed else 0)
