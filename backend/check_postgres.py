import asyncio
from sqlalchemy import text
from app.database import get_db

async def run_relational_audit():
    print("📡 SWEEPING POSTGRESQL TRANSACTIONAL LEDGERS VIA CODE IMPORTS...")
    
    async for db in get_db():
        try:
            # Audit A: Document State Matrix Check
            query_a = text("SELECT id, filename, status FROM knowledge_documents ORDER BY id DESC LIMIT 5;")
            result_a = await db.execute(query_a)
            rows_a = result_a.all()
            
            print("\n📁 1. DOCUMENT STATUS LEDGER MATRIX:")
            if not rows_a:
                print("   [Pristine Empty Ledger Row State]")
            for row in rows_a:
                print(f"   🔹 ID: {row.id} | Filename: {row.filename} | Status: {row.status}")
                
            # Audit B: Fragment Serialization Counts Check
            query_b = text("""
                SELECT document_id, COUNT(*) as total_chunks 
                FROM knowledge_chunks 
                GROUP BY document_id;
            """)
            result_b = await db.execute(query_b)
            rows_b = result_b.all()
            
            print("\n🧩 2. CHUNK STORAGE FRAGMENTATION COUNTS:")
            if not rows_b:
                print("   [0 Text Fragments Serialized]")
            for row in rows_b:
                print(f"   🔹 Doc ID Reference: {row.document_id} ──► Contains: {row.total_chunks} structured child text paragraphs")
                
        except Exception as exc:
            print(f"❌ REGISTRY ACCESS FAULT: {str(exc)}")
        break # Safely release connection pooling channels

if __name__ == "__main__":
    asyncio.run(run_relational_audit()) 