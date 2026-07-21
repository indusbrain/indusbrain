import os
import socket
import logging
import json
import traceback
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Suppress repetitive network checking logs from flooding terminals
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from app.database import engine, Base
from app.models.document import KnowledgeDocument
from app.models.chunk import KnowledgeChunk
from app.models.chat_history import ChatMessage

# Ingest all endpoint routers including our new predictive simulation module
from app.api.endpoints import ingestion, query, telemetry, simulator

from app.exceptions import (
    IndustrialBaseException, 
    AssetNotFoundException,
    industrial_exception_handler
)

logger = logging.getLogger("uvicorn.error")

class ASGIExceptionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            error_signature = traceback.format_exc().splitlines()[-1]
            log_payload = {
                "event": "CORE_PERIMETER_FAULT", "path": scope.get("path", "UNKNOWN"),
                "method": scope.get("method", "UNKNOWN"), "exception": type(exc).__name__, "signature": error_signature
            }
            logger.error(f"🚨 REASONING CORE FAULT ISOLATED: {json.dumps(log_payload)}")
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error_code": "INTERNAL_SYSTEM_CRASH", "message": "Secure transport layer fault isolation triggered."}
            )
            await response(scope, receive, send)

app = FastAPI(
    title="Industrial Knowledge Intelligence Platform (IKIP)",
    description="Enterprise-grade ASGI operational knowledge core grid.",
    version="1.0.0"
)

origins = ["*"] # Authorize global cross-origin development channels

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Register endpoint namespaces cleanly under /api/v1 namespace bounds
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(simulator.router, prefix="/api/v1") # 🎯 THE ROUTE FIX: Mounted the simulator endpoint cleanly

app.add_middleware(ASGIExceptionMiddleware)
app.add_exception_handler(IndustrialBaseException, industrial_exception_handler)
app.add_exception_handler(AssetNotFoundException, industrial_exception_handler)

@app.on_event("startup")
async def database_table_migration_handshake():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def read_root():
    return {"platform": "Industrial Knowledge Intelligence Platform (IKIP)", "status": "Operational"}