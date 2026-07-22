# IndusBrain — Team Setup Guide

A step-by-step guide to running IndusBrain after cloning the repository.

**Estimated time:** 30–45 minutes on first run (most of it downloading models).
**Disk space needed:** ~8 GB.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the repository](#2-clone-the-repository)
3. [Start the databases](#3-start-the-databases-docker)
4. [Set up the backend](#4-set-up-the-backend)
5. [Configure environment variables](#5-configure-environment-variables)
6. [Set up Ollama](#6-set-up-ollama)
7. [Run the backend](#7-run-the-backend)
8. [Set up and run the frontend](#8-set-up-and-run-the-frontend)
9. [Load the demo dataset](#9-load-the-demo-dataset)
10. [Verify everything works](#10-verify-everything-works)
11. [Troubleshooting](#11-troubleshooting)
12. [Daily start-up checklist](#12-daily-start-up-checklist)

---

## 1. Prerequisites

Install these before starting. Verify each one with the command shown.

| Software | Required version | Verify with | Download |
|---|---|---|---|
| **Python** | **3.11 exactly** | `python --version` | [python.org](https://www.python.org/downloads/release/python-3110/) |
| **Node.js** | 20 or newer | `node -v` | [nodejs.org](https://nodejs.org/) |
| **Docker Desktop** | latest | `docker --version` | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Ollama** | latest | `ollama --version` | [ollama.com](https://ollama.com/download) |
| **Git** | any recent | `git --version` | [git-scm.com](https://git-scm.com/) |
| **Tesseract OCR** | *optional* | `tesseract --version` | [UB-Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki) |

### Important notes

**Python must be 3.11.** Version 3.12+ has not been verified with this dependency set, and 3.14 is
known to fail (several packages have no pre-built wheels for it). If your system Python is newer,
install 3.11 alongside it and use its full path when creating the virtual environment.

**Docker Desktop must be running** before you continue — not just installed. Look for the whale icon
in your system tray.

**Tesseract is optional.** It is only used for scanned, image-only PDFs. Without it, digital PDFs still
index perfectly; scanned pages are skipped with a clear log message.

---

## 2. Clone the repository

```bash
git clone <repository-url>
cd indusbrain
```

You should see:

```
backend/  frontend/  docs/  Submission/  docker-compose.yml  README.md
```

---

## 3. Start the databases (Docker)

IndusBrain uses three databases, all managed by Docker Compose.

```bash
docker compose up -d
```

First run downloads about 1.5 GB of images — this takes a few minutes.

### Verify

```bash
docker compose ps
```

**Expected output** — three containers, all `Up`:

```
NAME                   IMAGE                    STATUS
industryos_chromadb    chromadb/chroma:0.5.0    Up
industryos_neo4j       neo4j:5.19-community     Up
industryos_postgres    postgres:16-alpine       Up
```

| Service | Purpose | Host port |
|---|---|---|
| PostgreSQL | Documents, passages, conversations | 5432 |
| Neo4j | Asset knowledge graph | 7687 (bolt), 7474 (browser) |
| ChromaDB | Vector index | 8001 |

> Neo4j takes 20–30 seconds to become ready after the container starts. If the backend reports it
> offline on first launch, wait and retry — it reconnects automatically.

---

## 4. Set up the backend

```bash
cd backend
```

### Create the virtual environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Your prompt should now start with `(.venv)`.

### Install dependencies

```bash
pip install -r requirements.txt
```

This installs about 2.5 GB (PyTorch is the bulk of it) and takes 5–10 minutes.

### Verify

```bash
python -c "import fastapi, sqlalchemy, chromadb, neo4j, fitz; print('backend dependencies OK')"
```

---

## 5. Configure environment variables

Create `backend/.env` with exactly this content:

```ini
# --- PostgreSQL ---
DATABASE_URL=postgresql://industrial_admin:secret_db_pass_2026@localhost:5432/industryos_core

# --- Neo4j (must match docker-compose.yml) ---
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secret_graph_pass_2026

# --- ChromaDB (published on 8001; container listens on 8000) ---
CHROMA_HOST=localhost
CHROMA_PORT=8001
ANONYMIZED_TELEMETRY=False

# --- Ollama ---
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120

# --- Authentication mode: demo | secure ---
AUTH_MODE=demo
SESSION_LIFETIME_HOURS=12

# --- Ingestion concurrency ---
INGEST_PAGE_WORKERS=8
INGEST_DOCUMENT_CONCURRENCY=2

# --- API ---
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
APP_ENV=development
```

> ⚠️ **Define each key exactly once.** If a key appears twice, the *last* value silently wins. A
> duplicated `NEO4J_PASSWORD` once disabled graph retrieval in this project for days without any
> visible error — the system just quietly fell back to vector-only search.

**Windows users:** if Tesseract is installed somewhere unusual, add:
```ini
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

## 6. Set up Ollama

Ollama runs the language model locally — no API keys, no cloud, no cost.

```bash
ollama pull qwen2.5:7b
```

This downloads ~4.7 GB. Grab a coffee.

### Verify

```bash
ollama list
```

**Expected:**
```
NAME              ID              SIZE      MODIFIED
qwen2.5:7b        845dbda0ea48    4.7 GB    ...
```

> If you already have a different model, IndusBrain will detect it and use it automatically, telling
> you which model answered. `qwen2.5:7b` gives the best results for this workload.

---

## 7. Run the backend

From `backend/`, with the virtual environment active:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Expected startup output:**

```
🟢 OCR ENGINE: Tesseract resolved at C:\Program Files\Tesseract-OCR\tesseract.exe
🟢 RERANKING CORE: Neural Cross-Encoder Transformer activated successfully.
🏆 LANGGRAPH MATRIX: Complete Multi-Agent Workflow Graph Compiled Successfully!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

> **First launch is slow** (2–3 minutes). It downloads two models from Hugging Face:
> the embedding model (~90 MB) and the re-ranker (~1.1 GB). Subsequent launches take seconds.

### Verify

Open **http://localhost:8000/docs** — you should see the interactive API documentation.

---

## 8. Set up and run the frontend

Open a **new terminal** (leave the backend running).

```bash
cd frontend
npm install
npm run dev
```

**Expected:**
```
VITE v8.1.4  ready in 412 ms
➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** — the IndusBrain Overview page should load.

---

## 9. Load the demo dataset

The repository includes a generator for a realistic Oil & Gas refinery corpus.

```bash
cd backend
python scripts/generate_refinery_corpus.py refinery_corpus
```

**Expected:**
```
  Machines/OEM_Manual_P-101A_Crude_Charge_Pump.pdf  (9.4 KB)
  ... 13 files total ...

Generated 13 refinery documents in 'refinery_corpus'.
```

### Upload them

1. In the app, set the sidebar role to **Manager**
2. Go to **Documents**
3. Drag the PDFs from `backend/refinery_corpus/` (all subfolders) into the upload area
4. Click **Upload documents**
5. Watch **Ingestion activity** — each document moves through
   *Queued → Extracting and indexing → Indexed*

Indexing 13 documents takes 2–4 minutes.

---

## 10. Verify everything works

### Automated check

```bash
cd backend
python scripts/smoke_test.py
```

**Expected:**
```
==========================================================
  PASSED: 43    FAILED: 0
==========================================================
```

### Manual checks

| # | Check | Expected result |
|---|---|---|
| 1 | **Overview** page | Knowledge score, 13 documents, 22 assets, 1 conflict |
| 2 | **Conflicts** page | P-101A discharge pressure: 285 PSI vs 340 PSI |
| 3 | **Knowledge Explorer** | Assets `P-101A`, `PSV-1201`, `K-2101`, `E-1501`… |
| 4 | **Ask IndusBrain** | Suggestions naming real assets from the corpus |
| 5 | Ask *"What is the discharge pressure limit for P-101A?"* | Cited answer, evidence panel with 4 sources |
| 6 | Click **Show evidence → Decision replay** | 5-step trace with real metrics |
| 7 | Switch role to **Engineer** | Documents page becomes read-only, no Upload/Delete |

### Health check commands

```bash
# API alive
curl http://localhost:8000/

# Databases running
docker compose ps

# Ollama model present
ollama list

# Document count
docker exec industryos_postgres psql -U industrial_admin -d industryos_core -c "SELECT count(*) FROM knowledge_documents;"
```

---

## 11. Troubleshooting

### `ModuleNotFoundError: No module named 'fitz'`

PyMuPDF is missing. **All ingestion will fail** with this error.

```bash
pip install PyMuPDF==1.28.0
```

---

### Uploads fail immediately — every document shows FAILED

Run the per-stage diagnostic to see exactly which stage breaks:

```bash
python scripts/diagnose_ingestion.py "refinery_corpus/Machines/Asset_Register_Unit100_CDU.pdf"
```

It reports page count, characters extracted per page, and chunk counts, so you can tell whether the
problem is extraction, OCR or chunking.

---

### Neo4j shows offline / no assets in Knowledge Explorer

1. Confirm the container is up: `docker compose ps`
2. Check `NEO4J_PASSWORD` in `.env` is `secret_graph_pass_2026` and appears **only once**
3. Rebuild the graph from Postgres without re-uploading:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/reindex-graph -H "X-IndusBrain-Role: manager"
```

---

### `Cannot reach the IndusBrain API`

- Is the backend terminal still running?
- Test directly: `curl http://localhost:8000/`
- If the port is stuck after a crash:

**Windows:**
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
```

---

### Port 8000 already in use after stopping the server

Ingestion worker threads can occasionally keep the socket open. Kill any stray Python processes:

**Windows:**
```powershell
Get-Process python | Stop-Process -Force
```

**macOS / Linux:**
```bash
pkill -f uvicorn
```

---

### `UnicodeEncodeError: 'charmap' codec can't encode character`

A Windows console using the legacy `cp1252` codepage. The app forces UTF-8 at startup, but if you see
this in a script, run:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

---

### Answers take 60–90 seconds

Normal for local CPU inference. Options:

- Switch the chat toggle to **Retrieval only** — instant, still fully cited
- Use a smaller model: `ollama pull qwen2.5:3b`, then set `OLLAMA_MODEL=qwen2.5:3b`

---

### Frontend shows "This section failed to render"

Usually a stale Vite module cache after pulling new code:

```bash
cd frontend
rm -rf node_modules/.vite
npm run dev
```

---

### `npm install` fails

```bash
rm -rf node_modules package-lock.json
npm install
```

Check `node -v` is 20 or newer.

---

### Everything is broken — full reset

> ⚠️ **This deletes all indexed documents and conversations.**

```bash
docker compose down -v
docker compose up -d
# wait ~30 seconds for Neo4j, then restart the backend
```

---

## 12. Daily start-up checklist

Once set up, this is all you need each day:

```bash
# 1. Databases
docker compose up -d

# 2. Backend (terminal 1)
cd backend
.venv\Scripts\activate        # Windows
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Frontend (terminal 2)
cd frontend
npm run dev
```

Open **http://localhost:5173**.

Ollama normally runs automatically in the background. If not: `ollama serve`.

---

## Getting help

1. Check the backend terminal — errors are logged with clear prefixes (🚨 for failures)
2. Run `python scripts/smoke_test.py` to identify which subsystem is failing
3. Use `diagnose_ingestion.py` or `diagnose_retrieval.py` to isolate a pipeline stage
4. See the [README](README.md) for architecture details

---

<div align="center">

**IndusBrain** — ET AI Hackathon 2026, Problem Statement 8

</div>
