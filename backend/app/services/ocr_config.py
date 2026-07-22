"""
Single source of truth for locating the Tesseract OCR binary.

Previously three separate modules each carried their own hardcoded list that
began with `D:\\Apps\\Tesseract\\tesseract.exe` — one developer's personal install
path. On any other machine those entries simply fail, and the lists had already
drifted out of sync with each other.

Resolution order:
  1. TESSERACT_CMD environment variable (explicit override)
  2. The system PATH
  3. Conventional install locations for the host platform
"""

import os
import platform
import shutil
from typing import List, Optional


def _candidate_paths() -> List[str]:
    """Conventional Tesseract locations for the current operating system."""
    system = platform.system()

    if system == "Windows":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(program_files, "Tesseract-OCR", "tesseract.exe"),
            os.path.join(program_files_x86, "Tesseract-OCR", "tesseract.exe"),
        ]
        if local_app_data:
            candidates.append(
                os.path.join(local_app_data, "Programs", "Tesseract-OCR", "tesseract.exe")
            )
        return candidates

    if system == "Darwin":
        return ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"]

    return ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]


def resolve_tesseract_binary() -> Optional[str]:
    """Returns the path to a usable Tesseract binary, or None if unavailable."""
    override = os.getenv("TESSERACT_CMD")
    if override and os.path.exists(override):
        return override

    on_path = shutil.which("tesseract")
    if on_path:
        return on_path

    for candidate in _candidate_paths():
        if os.path.exists(candidate):
            return candidate

    return None


# Resolved once at import; modules read these rather than probing themselves.
TESSERACT_BINARY: Optional[str] = resolve_tesseract_binary()
OCR_AVAILABLE: bool = TESSERACT_BINARY is not None
