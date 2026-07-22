"""
Dashboard telemetry.

Every number returned here is either a direct count from the database or a
clearly-defined ratio of such counts. There are no placeholder findings and no
constant offsets applied to make figures look healthier than they are.
"""

import os
import re
import socket
import time
from typing import Any, Dict, List

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import KnowledgeChunk
from app.models.document import KnowledgeDocument
from app.services.conflict_engine import industrial_conflict_engine

# Asset tags look like PUMP-101 / VALVE-220. The prefix list is restricted to real
# equipment classes so document reference numbers (ERN-2024, SOP-014, ISO-9001)
# are not misread as physical plant assets.
EQUIPMENT_TAG_PATTERN = re.compile(
    r"\b(PUMP|VALVE|PSV|COMP|MTR|BRG|HX|TK|FAN|BLR|ENG|SYS)-(\d{2,4}[A-Z]?)\b"
)

EQUIPMENT_CATEGORIES = {
    "PUMP": "Rotating - pump",
    "COMP": "Rotating - compressor",
    "FAN": "Rotating - fan",
    "MTR": "Electrical - motor",
    "VALVE": "Flow control - valve",
    "PSV": "Safety - relief valve",
    "HX": "Static - heat exchanger",
    "TK": "Static - tank",
    "BLR": "Static - boiler",
    "BRG": "Component - bearing",
    "ENG": "Rotating - engine",
    "SYS": "System",
}

# Evidence categories used for coverage scoring
COVERAGE_TERMS = {
    "maintenance": ("MAINTENANCE", "REPAIR", "SERVICE", "WORK ORDER", "OVERHAUL", "IOM"),
    "safety": ("SAFETY", "HAZARD", "RELIEF", "LOCKOUT", "ISOLATION", "WARNING", "PSV"),
    "procedure": ("PROCEDURE", "SOP", "STEP", "STARTUP", "SHUTDOWN", "CHANGEOVER"),
    "inspection": ("INSPECTION", "INSPECTED", "TEST", "CALIBRAT", "SURVEY", "AUDIT"),
}


# ---------------------------------------------------------------------------
# Short-lived cache
# ---------------------------------------------------------------------------
# The dashboard polls frequently. Without this, every poll from every open browser
# tab re-read the entire chunk table and re-ran conflict analysis over the whole
# corpus, which does not scale past a demo dataset.
_CACHE: Dict[str, Any] = {"expires_at": 0.0, "payload": None}
_CACHE_TTL_SECONDS = float(os.getenv("DASHBOARD_CACHE_TTL", "8"))


def _probe_tcp(host: str, port: int, timeout: float = 0.25) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "ONLINE"
    except Exception:
        return "OFFLINE"


async def _probe_ollama(host: str) -> Dict[str, Any]:
    """Reports Ollama status AND which models are actually installed."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            response = await client.get(f"{host}/api/tags")
        if response.status_code == 200:
            models = [m.get("name", "") for m in response.json().get("models", [])]
            return {"status": "ONLINE" if models else "NO_MODELS", "models": models}
    except Exception:
        pass
    return {"status": "OFFLINE", "models": []}


def _strip_parent(content: str) -> str:
    """Chunks are stored as 'child ||| parent'; the parent holds fuller context."""
    return content.split(" ||| ", 1)[1] if " ||| " in content else content


async def build_dashboard_payload(db: AsyncSession) -> Dict[str, Any]:
    # ---------------- Infrastructure ----------------
    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    ollama_state = await _probe_ollama(ollama_host)

    infrastructure = {
        "postgresql": _probe_tcp("127.0.0.1", 5432),
        "neo4j": _probe_tcp("127.0.0.1", int(os.getenv("NEO4J_PORT", 7687))),
        "chromadb": _probe_tcp("127.0.0.1", int(os.getenv("CHROMA_PORT", 8001))),
        "ollama_qwen": ollama_state["status"],
        "ollama_models": ollama_state["models"],
    }

    # ---------------- Document inventory ----------------
    documents_result = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc())
    )
    documents = documents_result.scalars().all()

    chunk_counts_result = await db.execute(
        select(KnowledgeChunk.document_id, func.count(KnowledgeChunk.id))
        .group_by(KnowledgeChunk.document_id)
    )
    chunks_per_document = dict(chunk_counts_result.all())

    inventory: List[Dict[str, Any]] = []
    seen_filenames = set()
    duplicate_documents = 0
    failed_documents = 0

    for doc in documents:
        if doc.filename in seen_filenames:
            duplicate_documents += 1
        seen_filenames.add(doc.filename)

        status_text = str(doc.status).split(".")[-1].upper()
        if status_text == "FAILED":
            failed_documents += 1

        inventory.append({
            "id": doc.id,
            "filename": doc.filename,
            "status": status_text,
            "chunk_count": chunks_per_document.get(doc.id, 0),
            "file_size": doc.file_size,
            "mime_type": doc.mime_type,
            "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
        })

    total_documents = len(documents)

    # ---------------- Corpus analysis ----------------
    chunk_rows_result = await db.execute(
        select(KnowledgeChunk.content, KnowledgeDocument.filename)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
    )
    chunk_rows = chunk_rows_result.all()

    asset_evidence: Dict[str, Dict[str, Any]] = {}
    category_hits = {key: 0 for key in COVERAGE_TERMS}
    scan_payload: List[Dict[str, str]] = []

    for content, filename in chunk_rows:
        text = _strip_parent(content or "")
        scan_payload.append({"content": text, "filename": filename})
        upper_text = text.upper()

        for category, terms in COVERAGE_TERMS.items():
            if any(term in upper_text for term in terms):
                category_hits[category] += 1

        for prefix, number in EQUIPMENT_TAG_PATTERN.findall(upper_text):
            tag = f"{prefix}-{number}"
            record = asset_evidence.setdefault(tag, {
                "tag": tag,
                "category": EQUIPMENT_CATEGORIES.get(prefix, "Unclassified"),
                "documents": set(),
                "mentions": 0,
                "evidence": {key: False for key in COVERAGE_TERMS},
            })
            record["documents"].add(filename)
            record["mentions"] += 1
            for category, terms in COVERAGE_TERMS.items():
                if any(term in upper_text for term in terms):
                    record["evidence"][category] = True

    # ---------------- Asset register + real documentation gaps ----------------
    assets: List[Dict[str, Any]] = []
    knowledge_gaps: List[Dict[str, Any]] = []

    for tag in sorted(asset_evidence):
        record = asset_evidence[tag]
        evidence = record["evidence"]
        missing = [name for name, present in evidence.items() if not present]

        assets.append({
            "tag": tag,
            "category": record["category"],
            "mentions": record["mentions"],
            "document_count": len(record["documents"]),
            "documents": sorted(record["documents"]),
            "coverage": evidence,
            "missing_coverage": missing,
            # "Complete" strictly means all four evidence categories were found.
            "status": "Documented" if not missing else "Gaps",
        })

        for missing_category in missing:
            knowledge_gaps.append({
                "id": f"gap_{tag}_{missing_category}",
                "asset": tag,
                "category": missing_category,
                "severity": "HIGH" if missing_category in ("safety", "inspection") else "MEDIUM",
                # States only what was actually observed. No invented overdue periods.
                "statement": (
                    f"No {missing_category} documentation was found for {tag} in the "
                    f"{len(record['documents'])} indexed document(s) that mention it."
                ),
            })

    # ---------------- Real cross-document conflicts ----------------
    conflict_report = industrial_conflict_engine.analyze_context_slices(scan_payload)
    conflicts = conflict_report["detected_anomalies"]

    # ---------------- Coverage metrics (plain ratios, no offsets) ----------------
    total_chunks = len(chunk_rows)

    def coverage_pct(category: str) -> float:
        if total_chunks == 0:
            return 0.0
        return round((category_hits[category] / total_chunks) * 100, 1)

    documented_assets = sum(1 for a in assets if not a["missing_coverage"])
    asset_completeness = (
        round((documented_assets / len(assets)) * 100, 1) if assets else 0.0
    )

    # Knowledge score = how completely assets are documented, reduced by unresolved
    # contradictions and failed ingestions. Every term is explained to the user.
    conflict_penalty = min(30, len(conflicts) * 10)
    failure_penalty = min(20, failed_documents * 5)
    knowledge_score = max(0, round(asset_completeness - conflict_penalty - failure_penalty, 1))

    return {
        "generated_at": time.time(),
        "infrastructure": infrastructure,
        "metrics": {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "total_assets": len(assets),
            "documented_assets": documented_assets,
            "knowledge_score": knowledge_score,
            "asset_completeness": asset_completeness,
            "maintenance_coverage": coverage_pct("maintenance"),
            "safety_coverage": coverage_pct("safety"),
            "procedure_coverage": coverage_pct("procedure"),
            "inspection_coverage": coverage_pct("inspection"),
            "documentation_gaps": len(knowledge_gaps),
            "duplicate_documents": duplicate_documents,
            "failed_documents": failed_documents,
            "open_conflicts": len(conflicts),
        },
        "score_breakdown": {
            "base_asset_completeness": asset_completeness,
            "conflict_penalty": conflict_penalty,
            "failure_penalty": failure_penalty,
            "formula": "knowledge_score = asset_completeness - conflict_penalty - failure_penalty",
            "explanation": (
                f"{documented_assets} of {len(assets)} tracked assets have maintenance, "
                f"safety, procedure and inspection evidence. "
                f"{len(conflicts)} unresolved contradiction(s) and "
                f"{failed_documents} failed ingestion(s) reduce the score."
            ) if assets else "No equipment tags have been extracted yet.",
        },
        "inventory": inventory,
        "assets": assets,
        "conflicts": conflicts,
        "knowledge_gaps": knowledge_gaps,
        "empty_states": {
            "no_documents": total_documents == 0,
            "no_assets": len(assets) == 0,
            "no_conflicts": len(conflicts) == 0,
            "conflicts_reason": conflict_report.get("empty_reason"),
        },
    }


async def get_dashboard_payload(db: AsyncSession, force_refresh: bool = False) -> Dict[str, Any]:
    now = time.time()
    if not force_refresh and _CACHE["payload"] is not None and now < _CACHE["expires_at"]:
        cached = dict(_CACHE["payload"])
        cached["cached"] = True
        return cached

    payload = await build_dashboard_payload(db)
    _CACHE["payload"] = payload
    _CACHE["expires_at"] = now + _CACHE_TTL_SECONDS
    result = dict(payload)
    result["cached"] = False
    return result


def invalidate_dashboard_cache() -> None:
    """Called after mutations so the dashboard reflects changes immediately."""
    _CACHE["payload"] = None
    _CACHE["expires_at"] = 0.0
