import os
import socket
import sys

def verify_port(host: str, port: int, service_name: str) -> bool:
    print(f"🔍 Analyzing route connectivity to [{service_name}] at {host}:{port}...")
    try:
        # Standard structural socket handshake test
        with socket.create_connection((host, port), timeout=3.0) as sock:
            print(f"🟢 SUCCESS: Secure line established with [{service_name}] container layer!")
            return True
    except (socket.timeout, ConnectionRefusedError):
        print(f"❌ FAILURE: Route to [{service_name}] is blocked or container is offline.")
        return False

def run_system_audit():
    print("====================================================")
    print("🚀 INDUSTRYOS DATA LAYER: CONNECTIVITY TELEMETRY DIAGNOSTIC")
    print("====================================================")
    
    # Target configurations matching docker network bounds
    targets = [
        ("localhost", 5432, "PostgreSQL relational engine"),
        ("localhost", 7687, "Neo4j graph database bolt link"),
        ("localhost", 8001, "ChromaDB high-performance vector store")
    ]
    
    audit_passed = True
    for host, port, name in targets:
        if not verify_port(host, port, name):
            audit_passed = False
            
    print("====================================================")
    if audit_passed:
        print("🏆 SCORECARD STATUS: 100% SUCCESS. Environment is fully active!")
        sys.exit(0)
    else:
        print("🚨 SCORECARD STATUS: DEGRADED. Ensure 'docker compose up -d' is running.")
        sys.exit(1)

if __name__ == "__main__":
    run_system_audit()