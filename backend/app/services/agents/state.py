import operator
from typing import List, Dict, Any, Annotated
from typing_extensions import TypedDict

def append_unique_records(current_records: List[Dict[str, Any]], new_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    State Reducer function. Merges text fragments or metadata packets 
    while filtering out duplicate entries using unique ID signatures.
    """
    if not current_records:
        return list(new_records) if new_records else []
    if not new_records:
        return list(current_records)

    # De-duplicate incoming records securely using dictionary lookups
    seen_ids = set()
    combined_accumulator = []

    for item in list(current_records) + list(new_records):
        # Tolerate non-dict entries (e.g. a bare filename string) instead of crashing
        # the whole graph run. Anything that is not a dict is keyed by its own text.
        if isinstance(item, dict):
            item_id = item.get("id") or item.get("s3_key") or str(item.get("content", ""))[:32]
        else:
            item_id = str(item)[:32]

        if item_id not in seen_ids:
            seen_ids.add(item_id)
            combined_accumulator.append(item)

    return combined_accumulator

class IndustryOSState(TypedDict):
    """
    Master Graph State Engine for the Industrial Knowledge Intelligence Platform.
    Acts as the single source of truth across all processing nodes.
    """
    # Core User Interface Input Parameter Parameters
    query: str

    # Engine selection passed in from the API layer ("LOCAL" or "FALLBACK").
    # This MUST be declared here: LangGraph only carries keys that exist as
    # channels on the state schema, and silently drops anything else.
    routing_mode: str

    # Context State Control Anchors
    current_agent: str
    
    # Annotated Lists - Using state reducers to cleanly append discoveries 
    # instead of overwriting historical agent logs
    extracted_docs: Annotated[List[Dict[str, Any]], append_unique_records]
    graph_entities: Annotated[List[Dict[str, Any]], append_unique_records]
    compliance_violations: Annotated[List[Dict[str, Any]], operator.add]
    failure_logs: Annotated[List[Dict[str, Any]], operator.add]
    
    # Internal Reasoning Path Audits (Records the order of which agent ran when)
    reasoning_path: Annotated[List[str], operator.add]

    # Auditable execution trace. Every node APPENDS a record of what it actually did
    # as it runs. This is the real Decision Replay: it is written by the nodes
    # themselves, never reconstructed afterwards by guessing from the question text.
    decision_trace: Annotated[List[Dict[str, Any]], operator.add]

    # Measured retrieval statistics (candidate counts, score spread, which engine
    # answered). Populated by the worker nodes from real values.
    retrieval_stats: Dict[str, Any]

    # Executive Metadata Scorecard Output Metrics
    confidence_score: float
    final_response: str