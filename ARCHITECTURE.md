# IndusBrain — Architecture Blueprint

> This is the condensed architecture reference. For the full narrative — pipeline
> diagrams, ingestion stages, honesty guarantees and setup — see [README.md](README.md).

---

## 1. Layered architecture

| Layer | Responsibility | Implemented with |
|---|---|---|
| **Presentation** | Enterprise workspace: streaming chat, evidence panel, knowledge explorer, analytics, impact assessment, document viewer, conversation history | React 19, TypeScript, Vite, Tailwind CSS v4 |
| **API** | Async REST + Server-Sent Events streaming, role enforcement on every route | FastAPI, Pydantic v2, Uvicorn |
| **Reasoning** | Supervisor-routed multi-agent state machine with a deterministic conflict engine | LangGraph, Ollama (`qwen2.5:7b`, local) |
| **Retrieval** | Parallel vector + graph search, reciprocal rank fusion, cross-encoder re-ranking | ChromaDB, Neo4j, `all-MiniLM-L6-v2`, `BAAI/bge-reranker-base` |
| **Knowledge** | Text extraction cascade, hierarchical parent/child chunking, asset-tag recognition, graph construction | PyMuPDF → pdfplumber → Tesseract |
| **Persistence** | Documents, passages, conversations, messages, users, sessions | PostgreSQL 16 via SQLAlchemy 2.0 async + asyncpg |

All inference runs locally through Ollama. The platform requires no cloud AI provider
and no API keys.

---

## 2. Request path for a question

```
Question
  → validity gate (rejects empty / stopword-only / too-short input before retrieval)
  → supervisor: classify intent, select specialist
  → parallel retrieval: ChromaDB vector search ‖ Neo4j graph traversal
  → reciprocal rank fusion
  → cross-encoder re-ranking
  → relevance floor, with an exemption for graph-corroborated passages
     and passages containing the exact asset tag that was asked about
  → specialist agent: grounded generation under its own directive
  → compiler: citations, measured confidence, organizational memory, decision replay
  → SSE stream to the client
```

Every stage emits a named SSE event, so the interface shows real pipeline progress
rather than a decorative spinner.

---

## 3. Knowledge graph model

```
(:Document)-[:CONTAINS]->(:Chunk)-[:MENTIONS]->(:Asset)
(:Document)-[:REFERENCES]->(:Standard)
(:Asset)-[:GOVERNED_BY]->(:Standard)
```

Asset recognition is centralised in a single module (`backend/app/services/asset_tags.py`)
and supports two tagging conventions:

| Convention | Examples | Typical use |
|---|---|---|
| Descriptive | `PUMP-101`, `VALVE-1010`, `PSV-1201` | Maintenance systems, smaller sites |
| ISA / process | `P-101A`, `E-1501`, `K-2101`, `TK-1001` | Refineries and chemical plants |

Document, standard and work-order references (`SOP-`, `RCA-`, `WO-`, `API-`, `OSHA-`, …)
are explicitly excluded so they never pollute the asset register.

---

## 4. Agents

| Agent | Trigger | Behaviour |
|---|---|---|
| **Knowledge Agent** | Specifications, design data, general lookup | Answers with the stated values and their source |
| **Reliability Agent** | Failures, maintenance, root cause | Builds a dated chronology across documents |
| **Compliance Agent** | Standards, safety, regulatory obligations | Frames the answer as obligations and their status |
| **Conflict Agent** | Contradiction questions | Deterministic comparison engine, not RAG — no single passage can state that two documents disagree |

Each retrieval specialist carries its own generation directive and domain vocabulary.
The vocabulary influences passage ordering only; it never influences the reported
confidence score.

---

## 5. Trust and honesty guarantees

| Guarantee | Mechanism |
|---|---|
| Confidence is measured, not decorative | Computed from retrieval quality; capped at 95% |
| Citations are real | Only passages actually supplied to the model are cited |
| No invented dates | Dates appear only when present in the source text |
| Off-domain questions are refused | 0% confidence, 0 citations |
| Impact assessment refuses rather than guesses | The heuristic metric engine was removed entirely |

---

## 6. Security model

- Role-based access control (Manager / Engineer) enforced **server-side** on every endpoint.
- Full authentication — bcrypt password hashing and opaque, revocable server-side session
  tokens — is implemented and activated with `AUTH_MODE=secure`.
- The hackathon build ships with `AUTH_MODE=demo` so judges can switch roles instantly
  without creating accounts. No security code is removed in demo mode; only the login
  requirement is bypassed.

---

## 7. Team roster

| Name | Area |
|---|---|
| *Prem Kajiwala* | Frontend architecture (React, TypeScript, Vite) |
| *Team member 2* | Backend and data layer (FastAPI, PostgreSQL, SQLAlchemy) |
| *Team member 3* | Multi-agent AI workflows and infrastructure (LangGraph, Neo4j, ChromaDB, Docker) |

> Keep this table in step with the contributors table in [README.md](README.md#contributors).
