import os
import subprocess

def extract_single_page_compute_task(args: tuple) -> str:
    """
    Isolated Multi-Core Compute Worker. Kept completely free of database,
    FastAPI, and framework dependencies to prevent re-import initialization logs.
    """
    file_path, page_idx, document_id = args
    page_text = ""
    
    # --- Engine Tier 1: PyMuPDF Streaming Character Extraction ---
    try:
        import fitz
        with fitz.open(file_path) as doc:
            if page_idx < len(doc):
                page_text = doc[page_idx].get_text("text")
    except Exception:
        pass
        
    # --- Engine Tier 2: pdfplumber Spatial Fallback Layout ---
    if not page_text or not page_text.strip():
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                if page_idx < len(pdf.pages):
                    page_text = pdf.pages[page_idx].extract_text()
        except Exception:
            pass
            
    # --- Engine Tier 3: Subprocess Tesseract Optical OCR Fallback ---
    if not page_text or not page_text.strip():
        tess_executables = [
            r"D:\Apps\Tesseract\tesseract.exe",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            "tesseract"
        ]
        temp_dir = os.path.join("storage", "temp_ocr")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            import fitz
            with fitz.open(file_path) as doc:
                if page_idx < len(doc):
                    page = doc[page_idx]
                    pix = page.get_pixmap(dpi=150)
                    tmp_img_path = os.path.join(temp_dir, f"mp_{document_id}_{page_idx}.png")
                    pix.save(tmp_img_path)
                    
                    out_base_path = os.path.join(temp_dir, f"txt_{document_id}_{page_idx}")
                    
                    for exe in tess_executables:
                        try:
                            subprocess.run(
                                [exe, tmp_img_path, out_base_path],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=25, check=True
                            )
                            txt_file = out_base_path + ".txt"
                            if os.path.exists(txt_file):
                                with open(txt_file, "r", encoding="utf-8") as f:
                                    page_text = f.read()
                                os.remove(txt_file)
                                break
                        except Exception:
                            continue
                            
                    if os.path.exists(tmp_img_path):
                        os.remove(tmp_img_path)
        except Exception:
            pass
            
    return page_text if page_text else ""