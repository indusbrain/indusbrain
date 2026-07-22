"""
Runs the ingestion pipeline stages against a PDF and reports exactly which stage
fails, so an ingestion failure can be diagnosed without reading server logs.

Usage:  python scripts/diagnose_ingestion.py <file.pdf> [more.pdf ...]
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from app.api.endpoints.ingestion import (  # noqa: E402
    count_pdf_pages,
    extract_single_page_compute_task,
    sanitize_text_payload,
)
from app.services.chunker import cognitive_chunker  # noqa: E402


def diagnose(path: str) -> None:
    print(f"\n=== {os.path.basename(path)} ===")
    if not os.path.exists(path):
        print("  file not found")
        return

    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  size: {size_mb:.2f} MB")

    try:
        pages = count_pdf_pages(path)
        print(f"  [1] page count      : {pages}")
        if pages <= 0:
            print("      FAIL - neither PyMuPDF nor pdfplumber could open this file")
            return

        sample = min(pages, 5)
        texts = []
        for index in range(sample):
            text = extract_single_page_compute_task((path, index, 999))
            texts.append(text)
            print(f"      page {index + 1}: {len(text)} chars")

        joined = sanitize_text_payload("\n".join(texts))
        print(f"  [2] extracted text  : {len(joined)} chars from {sample} page(s)")

        if not joined.strip():
            print("      FAIL - extraction produced no text (image-only PDF and OCR unavailable?)")
            from app.services.ocr_config import OCR_AVAILABLE, TESSERACT_BINARY

            print(f"      OCR available: {OCR_AVAILABLE} ({TESSERACT_BINARY})")
            return

        chunks = cognitive_chunker.generate_hierarchical_chunks(joined)
        children = sum(len(c["children"]) for c in chunks)
        print(f"  [3] chunking        : {len(chunks)} parents / {children} children")
        if children == 0:
            print("      FAIL - chunker produced no children")
            return

        print("  RESULT: pipeline stages OK for this file")

    except Exception as error:
        print(f"  EXCEPTION at pipeline stage: {type(error).__name__}: {error}")
        traceback.print_exc()


if __name__ == "__main__":
    targets = sys.argv[1:]
    if not targets:
        print(__doc__)
        sys.exit(1)
    for target in targets:
        diagnose(target)
