import operator
from typing import List, Dict, Any, Annotated
from typing_extensions import TypedDict

def append_unique_records(current_records: List[Dict[str, Any]], new_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    State Reducer function. Merges text fragments or metadata packets 
    while filtering out duplicate entries using unique ID signatures.
    """
    if not current_records:
        return new_records if new_records else []
    if not new_records:
        return current_records

    # De-duplicate incoming records securely using dictionary lookups
    seen_ids = set()
    combined_accumulator = []

    for item in current_records + new_records:
        # Generate an absolute unique key signature check using document hashes or titles
        item_id = item.get("id") or item.get("s3_key") or str(item.get("content", ""))[:32]
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
    
    # Executive Metadata Scorecard Output Metrics
    confidence_score: float
    final_response: str