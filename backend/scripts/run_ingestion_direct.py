"""
Runs the REAL background ingestion coroutine against a file and surfaces the
exception, instead of it being swallowed into a FAILED status.

Usage:  python scripts/run_ingestion_direct.py <document_id> <file_path> <filename>
"""

import asyncio
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


async def main() -> None:
    from app.api.endpoints.ingestion import orchestrate_background_ingestion

    document_id = int(sys.argv[1])
    file_path = sys.argv[2]
    filename = sys.argv[3]

    print(f"Running ingestion for doc {document_id}: {file_path}")
    try:
        await orchestrate_background_ingestion(document_id, file_path, filename)
        print("ingestion coroutine returned without raising")
    except Exception:
        print("EXCEPTION ESCAPED:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
