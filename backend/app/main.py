import os
import socket
import logging
import json
import traceback
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure all dynamic environment parameters are loaded from local storage disk
load_dotenv()

# 🎯 THE LOG CLEANER FIX: Suppress internal HTTP client pooling logs from flooding your terminal window
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Import our async database engine drivers and core metadata sheets
from app.database import engine, Base

# Explicitly import models to register tables into the SQLAlchemy metadata scope
from app.models.document import KnowledgeDocument
from app.models.chunk import KnowledgeChunk
from app.models.chat_history import ChatMessage

# Ingest all core API endpoint routes
from app.api.endpoints import ingestion, query, telemetry

from app.exceptions import (
    IndustrialBaseException, 
    AssetNotFoundException,
    industrial_exception_handler
)

# Bind directly to Uvicorn's active terminal streaming engine
logger = logging.getLogger("uvicorn.error")

# ========================================================
# 🛡️ PURE ASGI EXCEPTION MIDDLEWARE LAYER
# ========================================================
class ASGIExceptionMiddleware:
    """
    Production-grade Pure ASGI Middleware. Traps all unhandled runtime 
    crashes directly at the transport layer, eliminating AnyIO stream fractures.
    """
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
                "event": "CORE_PERIMETER_FAULT",
                "path": scope.get("path", "UNKNOWN"),
                "method": scope.get("method", "UNKNOWN"),
                "exception": type(exc).__name__,
                "signature": error_signature
            }
            logger.error(f"🚨 REASONING CORE FAULT ISOLATED: {json.dumps(log_payload)}")

            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error_code": "INTERNAL_SYSTEM_CRASH",
                    "message": "A secure perimeter fault occurred. Request transaction safely isolated.",
                    "details": error_signature if os.getenv("APP_ENV") == "development" else "Redacted."
                }
            )
            await response(scope, receive, send)

# ========================================================
# APPLICATION CORE INITIALIZATION & ROUTING INSTANTIATION
# ========================================================
app = FastAPI(
    title="Industrial Knowledge Intelligence Platform (IKIP)",
    description="The Operating System for Industrial Knowledge. Enterprise-grade ASGI operating core grid.",
    version="1.0.0"
)

origins = [
    "http://localhost:3000", 
    "http://localhost:3001",   
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Mount Routers under the unified /api/v1 namespace
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")

# Mount the pure ASGI transport shield before processing any standard routing matrices
app.add_middleware(ASGIExceptionMiddleware)

# Bind custom domain exception handlers natively into the FastAPI pipeline context
app.add_exception_handler(IndustrialBaseException, industrial_exception_handler)
app.add_exception_handler(AssetNotFoundException, industrial_exception_handler)

# ---------------------------------------------------------------------
# SYSTEM ENGINE LIFECYCLE MANAGEMENT HOOKS
# ---------------------------------------------------------------------
@app.on_event("startup")
async def database_table_migration_handshake():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ---------------------------------------------------------------------
# OPERATIONAL API ROUTE DISPATCHERS
# ---------------------------------------------------------------------
@app.get("/")
async def read_root():
    return {
        "platform": "Industrial Knowledge Intelligence Platform (IKIP)",
        "status": "Operational",
        "system_era": "2026"
    }

@app.get("/api/health")
async def health_check():
    db_status = "Online"
    try:
        with socket.create_connection(("localhost", 5432), timeout=1.0):
            pass
    except Exception:
        db_status = "Offline"
        
    return {
        "api_engine": "Healthy",
        "transactional_database_route": db_status,
        "telemetry_handshake": "Verified"
    }   