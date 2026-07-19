import asyncio
import sys
import os
import shutil

# Append current directory to system path for clean application imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models.document import KnowledgeDocument
from app.models.chunk import KnowledgeChunk
from app.models.chat_history import ChatMessage

def clear_directory_path(target_dir: str):
    """ Safely clears all files inside a directory without deleting the directory itself """
    if os.path.exists(target_dir):
        print(f"🧹 Clearing directory items inside: {target_dir}")
        for item in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"   ⚠️ Could not remove file {item}: {str(e)}")
    else:
        print(f"📁 Directory not found, creating baseline folder: {target_dir}")
        os.makedirs(target_dir, exist_ok=True)

async def execute_absolute_zero_reset():
    print("======================================================================")
    print("☣️ CRITICAL CORE OPERATIONS: RUNNING ABSOLUTE ZERO PLATFORM PURGE")
    print("======================================================================\n")

    # 1. Clear Local Filesystem Storage & OCR Cache Zones
    print("📁 STEP 1: Purging cached document and image files from local disk...")
    clear_directory_path(os.path.join("storage", "documents"))
    clear_directory_path(os.path.join("storage", "text_cache"))
    clear_directory_path(os.path.join("storage", "temp_ocr"))
    
    # Optional ChromaDB directory wipe if configured locally on disk
    chroma_dir = os.path.join("storage", "chroma")
    if os.path.exists(chroma_dir):
        clear_directory_path(chroma_dir)

    print("🟢 Filesystem caches cleared successfully.\n")

    # 2. Reset Relational Database Schema Tables inside PostgreSQL
    print("💾 STEP 2: Connecting to PostgreSQL pool to drop database tables...")
    try:
        async with engine.begin() as conn:
            print("   💥 Dropping relational tables (Documents, Chunks, Chat Sessions)...")
            await conn.run_sync(Base.metadata.drop_all)
            
            print("   🧱 Building fresh database schemas from system templates...")
            await conn.run_sync(Base.metadata.create_all)
            
        print("🟢 PostgreSQL database tables re-initialized to empty states.\n")
        print("🏁 SYSTEM HARD RESET MANIFEST COMPLETE: Platform is now at Absolute Zero.")
        print("You can safely boot your uvicorn engines and run pristine tests.")
        
    except Exception as fatal_err:
        print(f"❌ CRITICAL TRANSACTIONS REJECTION FAULT: {str(fatal_err)}")

if __name__ == "__main__":
    asyncio.run(execute_absolute_zero_reset())