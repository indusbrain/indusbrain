import anyio
import asyncio
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
# 🟢 Target your project's compiled graph workflow engine instance
from app.services.agents.graph import compiled_agent_workflow

router = APIRouter(prefix="/query", tags=["Industrial AI Agent Core"])

# =====================================================================
# 📊 STRUCTURED VALIDATION SCHEMAS (Pydantic Models)
# =====================================================================
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

# =====================================================================
# 🔌 PORTAL A: UNARY HTTP POST PORTAL (REST Sandbox)
# =====================================================================
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

    # Initialize our central thread-safe state clipboard dictionary
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
        # Offload the heavy blocking state machine loop execution onto our background worker thread pool
        final_processed_state = await anyio.to_thread.run_sync(
            compiled_agent_workflow.invoke,
            initial_graph_state
        )

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

# =====================================================================
# 🌊 PORTAL B: ASYNCHRONOUS SSE STREAM GATEWAY (Production UI Hook)
# =====================================================================
@router.post("/stream", status_code=status.HTTP_200_OK)
async def stream_operator_query_loop(payload: QueryRequestPayload):
    """
    Spawns the compiled LangGraph Multi-Agent Core and opens a long-lived 
    Server-Sent Events (SSE) token stream to return responses character-by-character.
    """
    user_input_string = payload.query.strip()
    if not user_input_string:
        raise HTTPException(status_code=400, detail="Query text cannot be blank.")

    async def token_stream_generator():
        try:
            initial_graph_state = {
                "query": user_input_string,
                "current_agent": "orchestrator",
                "extracted_docs": [],
                "graph_entities": [],
                "compliance_violations": [],
                "failure_logs": [],
                "reasoning_path": [],
                "confidence_score": 0.0,
                "final_response": ""
            }

            # Invoke the graph workflow engine inside our background processing pool
            final_processed_state = await anyio.to_thread.run_sync(
                compiled_agent_workflow.invoke,
                initial_graph_state
            )
            
            compiled_report_text = final_processed_state.get("final_response", "Failed to compile final report.")

            # Chunk the compiled markdown text by word tokens to feed our streaming pipeline
            word_tokens_list = compiled_report_text.split(" ")
            for token in word_tokens_list:
                # Format string data strictly using the required SSE structure (\n\n is mandatory)
                yield f"data: {token} \n\n"
                await asyncio.sleep(0.03)

        except Exception as exc:
            yield f"data: ❌ CRITICAL STREAM GATEWAY EXCEPTION: {str(exc)} \n\n"

    return StreamingResponse(
        token_stream_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )