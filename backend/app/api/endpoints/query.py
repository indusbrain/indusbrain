import anyio
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.services.agents.graph import compiled_agent_workflow

router = APIRouter(prefix="/query", tags=["Industrial AI Agent Core"])

# Define structured request validation schemas
class QueryRequestPayload(BaseModel):
    query: str = Field(
        ..., 
        example="When was the centrifugal pump last serviced and is it under OSHA safety violations?",
        description="The raw physical operator question submitted from the plant floor."
    )

class QueryResponsePayload(BaseModel):
    response: str = Field(..., description="The compiled, markdown-formatted final response report.")
    confidence_score: float = Field(..., description="Calculated metric representing data-availability and system assurance.")
    reasoning_path: List[str] = Field(..., description="Auditable node execution trail showing the decision-making process.")
    current_agent: str = Field(..., description="The final agent node that processed the state before termination.")

@router.post("/submit", response_model=QueryResponsePayload, status_code=status.HTTP_200_OK)
async def submit_operator_query(payload: QueryRequestPayload):
    """
    Unified Ingestion Portal for Industrial Operations. Accepts operator queries,
    orchestrates specialized agent node execution cycles, and returns synthesized reports.
    """
    if not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User query context cannot be empty."
        )

    # 1. Initialize our central thread-safe state clipboard dictionary
    initial_graph_state = {
        "query": payload.query,
        "current_agent": "orchestrator",
        "extracted_docs": [],
        "graph_entities": [],
        "compliance_violations": [],
        "failure_logs": [],
        "reasoning_path": [],
        "confidence_score": 0.0,
        "final_response": ""
    }

    try:
        # 2. Offload the heavy blocking state machine loop execution onto our background worker thread pool
        # This keeps FastAPI's main event loop completely responsive to other network traffic
        final_processed_state = await anyio.to_thread.run_sync(
            compiled_agent_workflow.invoke,
            initial_graph_state
        )

        # 3. Construct and return the structured response payload
        return QueryResponsePayload(
            response=final_processed_state.get("final_response", "Failed to compile final report."),
            confidence_score=final_processed_state.get("confidence_score", 0.0),
            reasoning_path=final_processed_state.get("reasoning_path", []),
            current_agent=final_processed_state.get("current_agent", "compiler_node")
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow execution collapsed: {str(exc)}"
        )