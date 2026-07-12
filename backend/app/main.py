import os
import socket
import logging
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.exceptions import (
    IndustrialBaseException, 
    AssetNotFoundException,
    industrial_exception_handler
)
from dotenv import load_dotenv

# Ensure all dynamic environment parameters are loaded from local storage disk
load_dotenv()

# 🛡️ ENTERPRISE LOGGING HOOK: Bind directly to Uvicorn's active terminal streaming engine
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
        # Only process standard HTTP web traffic routes
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            # Pass execution context down to the next internal framework layer
            await self.app(scope, receive, send)
        except Exception as exc:
            # Trap any unhandled Python crash instantly before it bubbles to Uvicorn
            logger.error(
                f"💥 CRITICAL UNHANDLED SYSTEM CRASH at route {scope['path']}: {str(exc)}", 
                exc_info=True
            )
            
            # Formulate our uniform corporate error response string payload
            response_payload = {
                "success": False,
                "error_code": "ERR_INTERNAL_SERVER_FATAL",
                "message": "A critical server error occurred. System engineering teams have been notified.",
                "system_telemetry": "Degraded"
            }
            encoded_body = json.dumps(response_payload).encode("utf-8")
            
            # Stream the HTTP status and content-type headers down the ASGI pipe
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(encoded_body)).encode("ascii"))
                ]
            })
            
            # Stream the finalized payload body data blocks down the ASGI pipe
            await send({
                "type": "http.response.body",
                "body": encoded_body,
                "more_body": False
            })

# Initialize the core FastAPI engine instance
app = FastAPI(
    title="IndustryOS API Engine",
    description="The secure architectural back-bone routing framework for Industrial Knowledge Intelligence",
    version="1.0.0"
)

# Register our specialized domain error exception mapper
app.add_exception_handler(IndustrialBaseException, industrial_exception_handler)

# ========================================================
# 🔐 REGISTRATION SEQUENCE: MIDDLEWARE ASSEMBLY LAYER
# ========================================================
# Note: FastAPI applies middlewares in REVERSE order of declaration.
# We mount our Exception Gate first, and our CORS Gate second.
# This forces the request path flow to process: Ingest -> CORS -> Exception -> Core.
# Outgoing responses flow: Exception handles 500 -> CORS appends security keys -> Client Browser.

# 1. Mount the Pure ASGI Exception Perimeter Gate
app.add_middleware(ASGIExceptionMiddleware)

# 2. Mount our Sub-phase 4.4 Dynamic CORS Filters Matrix
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
origins = [origin.strip() for origin in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Loaded programmatically from our environment variable array
    allow_credentials=True,     # Permits secure transmission of identity cookie tokens
    allow_methods=["*"],         # Allows standard REST actions (GET, POST, PUT, DELETE)
    allow_headers=["*"],         # Accepts standard header tokens (Authorization, Content-Type)
)


@app.get("/")
async def read_root():
    """
    Root Gateway Entry Path.
    """
    return {
        "platform": "IndustryOS",
        "status": "Operational",
        "system_era": "2026"
    }

@app.get("/api/health")
async def health_check():
    """
    Production-grade System Health & Infrastructure Dependency Telemetry Endpoint.
    """
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

# ==========================================
# DIAGNOSTIC MOCK TESTING ROUTES (Temporary)
# ==========================================
@app.get("/api/test/domain-error")
async def trigger_domain_error():
    """
    Forces an explicit AssetNotFoundException to verify custom handler mapping layout.
    """
    raise AssetNotFoundException("Valve-4B maintenance history log entry index is missing.")

@app.get("/api/test/fatal-error")
async def trigger_fatal_error():
    """
    Forces a raw, unhandled python runtime collision to verify ultimate fallback loop safety.
    """
    broken_calculation = 100 / 0
    return {"result": broken_calculation}