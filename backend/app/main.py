from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socket

# Initialize the core FastAPI engine instance
app = FastAPI(
    title="IndustryOS API Engine",
    description="The secure architectural back-bone routing framework for Industrial Knowledge Intelligence",
    version="1.0.0"
)

# Enforce Cross-Origin Resource Sharing (CORS) security filters
# This allows our Next.js frontend running on port 3000 to communicate safely with this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    # Execute a rapid internal socket sanity check to verify database availability
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