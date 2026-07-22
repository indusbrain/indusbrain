"""
Full-system verification.

Exercises the complete stack against the LIVE application: infrastructure
connectivity, the document lifecycle (upload -> OCR/extraction -> chunking ->
embeddings -> knowledge graph), retrieval, and cleanup across all three stores.

Usage:  python system_verify.py
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"

passed, failed = 0, 0
failures = []


def check(label, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        failures.append(f"{label} :: {detail}")
        print(f"  [FAIL] {label}  {detail}")


def get(path, timeout=120):
    with urllib.request.urlopen(f"{API}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def post(path, payload=None, timeout=600):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


print("\n" + "=" * 70)
print("1. BACKEND AND INFRASTRUCTURE")
print("=" * 70)

try:
    with urllib.request.urlopen(f"{BASE}/", timeout=20) as r:
        check("backend responds", r.status == 200)
except Exception as e:
    check("backend responds", False, str(e))
    sys.exit(1)

dashboard = get("/telemetry/dashboard?refresh=true")
infra = dashboard["infrastructure"]
check("PostgreSQL reachable", infra["postgresql"] == "ONLINE", infra["postgresql"])
check("Neo4j reachable", infra["neo4j"] == "ONLINE", infra["neo4j"])
check("ChromaDB reachable", infra["chromadb"] == "ONLINE", infra["chromadb"])
check("Ollama reachable", infra["ollama_qwen"] == "ONLINE", infra["ollama_qwen"])
check("Ollama has a usable model", len(infra["ollama_models"]) > 0, str(infra["ollama_models"]))

print("\n" + "=" * 70)
print("2. DOCKER SERVICES")
print("=" * 70)
try:
    out = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
        capture_output=True, text=True, timeout=60,
    ).stdout
    running = {
        line.split("|")[0]: line.split("|")[1]
        for line in out.strip().splitlines() if "|" in line
    }
    for name in ("industryos_postgres", "industryos_neo4j", "industryos_chromadb"):
        check(f"{name} container up", name in running and running[name].startswith("Up"),
              running.get(name, "not running"))
except Exception as e:
    check("docker inspect", False, str(e))

print("\n" + "=" * 70)
print("3. DOCUMENT LIFECYCLE (upload -> extract -> chunk -> embed -> graph)")
print("=" * 70)

sample = os.path.join("sample_corpus", "Safety_Standard_Pressure_Systems.pdf")
if not os.path.exists(sample):
    check("sample document available", False, sample)
else:
    boundary = "----IndusBrainVerify"
    with open(sample, "rb") as fh:
        content = fh.read()

    body = b"".join([
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="files"; filename="VERIFY_lifecycle.pdf"\r\n',
        b"Content-Type: application/pdf\r\n\r\n",
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ])

    req = urllib.request.Request(
        f"{API}/ingestion/upload", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        upload = json.loads(r.read().decode())

    doc_id = upload["queue_manifest"][0]["id"]
    check("upload accepted", doc_id is not None, str(upload))

    final_stage = None
    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(3)
        stage = get(f"/ingestion/status/{doc_id}")["current_pipeline_stage"].split(".")[-1]
        if stage in ("EMBEDDED", "FAILED"):
            final_stage = stage
            break

    check("ingestion reached a terminal state", final_stage is not None, "timed out")
    check("ingestion succeeded (extraction + OCR fallback)", final_stage == "EMBEDDED", str(final_stage))

    after = get("/telemetry/dashboard?refresh=true")
    doc_row = next((d for d in after["inventory"] if d["id"] == doc_id), None)
    check("document appears in inventory", doc_row is not None)
    check("chunking produced passages", bool(doc_row) and doc_row["chunk_count"] > 0,
          str(doc_row["chunk_count"]) if doc_row else "n/a")

    # Verify the derived stores actually received this document.
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from app.services.vector_store import vector_store_engine
        from app.services.graph_store import graph_store_engine

        vectors = vector_store_engine.collection.get(where={"document_id": doc_id})
        check("embeddings written to ChromaDB", len(vectors["ids"]) > 0, str(len(vectors["ids"])))

        with graph_store_engine.driver.session() as s:
            n = s.run(
                "MATCH (d:Document {id:$i})-[:HAS_CHUNK]->(c:Chunk) RETURN count(c) AS n",
                i=doc_id,
            ).single()["n"]
        check("knowledge graph nodes created", n > 0, str(n))
    except Exception as e:
        check("derived store verification", False, str(e))

    print("\n" + "=" * 70)
    print("4. DELETION ACROSS ALL THREE STORES")
    print("=" * 70)

    req = urllib.request.Request(f"{API}/telemetry/document/{doc_id}", method="DELETE")
    with urllib.request.urlopen(req, timeout=180) as r:
        deleted = json.loads(r.read().decode())
    check("delete returned success", deleted["status"] == "DELETED", str(deleted))

    after_delete = get("/telemetry/dashboard?refresh=true")
    check("removed from Postgres inventory",
          all(d["id"] != doc_id for d in after_delete["inventory"]))

    try:
        vectors = vector_store_engine.collection.get(where={"document_id": doc_id})
        check("vectors purged from ChromaDB", len(vectors["ids"]) == 0, str(len(vectors["ids"])))
        with graph_store_engine.driver.session() as s:
            n = s.run(
                "MATCH (d:Document {id:$i})-[:HAS_CHUNK]->(c:Chunk) RETURN count(c) AS n",
                i=doc_id,
            ).single()["n"]
        check("graph nodes purged from Neo4j", n == 0, str(n))
    except Exception as e:
        check("derived store cleanup verification", False, str(e))

print("\n" + "=" * 70)
print("5. RETRIEVAL AND REASONING")
print("=" * 70)

answer = post("/query/submit",
              {"query": "What is the maximum discharge pressure for PUMP-101?",
               "routing_mode": "FALLBACK"})
check("hybrid retrieval returns citations", len(answer["citations"]) > 0)
check("graph corroboration present",
      any(c["origin"] == "HYBRID_GRAPH_VECTOR_VERIFIED" for c in answer["citations"]),
      str([c["origin"] for c in answer["citations"]]))
check("decision trace recorded", len(answer["decision_replay_path"]) >= 3)

conflicts = post("/ingestion/scan-conflicts")
check("conflict detection runs", "detected_anomalies" in conflicts)
check("the known PUMP-101 contradiction is detected",
      any(a["asset_tag"] == "PUMP-101" for a in conflicts["detected_anomalies"]),
      str([a["asset_tag"] for a in conflicts["detected_anomalies"]]))

sim = post("/simulator/simulate",
           {"scenario": "Delay maintenance by one week", "asset_tag": "PUMP-101"})
check("simulator returns metrics", "metrics" in sim)

history = get("/query/history/behaviour-suite")
check("session history persists", history["message_count"] > 0, str(history["message_count"]))

print("\n" + "=" * 70)
print(f"  PASSED: {passed}    FAILED: {failed}")
for f in failures:
    print(f"   - {f}")
print("=" * 70)
sys.exit(1 if failed else 0)
