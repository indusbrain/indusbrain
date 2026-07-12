from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.exceptions import (
    IndustrialBaseException, 
    AssetNotFoundException,
    industrial_exception_handler, 
    global_unhandled_exception_handler
)
import socket

# Initialize the core FastAPI engine instance
app = FastAPI(
    title="IndustryOS API Engine",
    description="The secure architectural back-bone routing framework for Industrial Knowledge Intelligence",
    version="1.0.0"
)

# Enforce Cross-Origin Resource Sharing (CORS) security filters
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register our Centralized Global Error Interceptor Patterns
app.add_exception_handler(IndustrialBaseException, industrial_exception_handler)
app.add_exception_handler(500, global_unhandled_exception_handler)


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
    # Intentional division by zero code error to trigger a fatal system fault
    broken_calculation = 100 / 0
    return {"result": broken_calculation}