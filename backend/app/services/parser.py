import os
import shutil
import pytesseract

# 🛡️ PRODUCTION RESILIENCY GATE: Resolve Tesseract command location
tesseract_bin = shutil.which("tesseract")

if tesseract_bin:
    # If the system path is working, use it directly
    pytesseract.pytesseract.tesseract_cmd = tesseract_bin
    print(f"🟢 OCR ENGINE: Tesseract verified on system PATH: {tesseract_bin}")
else:
    # Fallback: Check the standard default installation directories on Windows
    default_windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]
    
    patched = False
    for path in default_windows_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"🎯 OCR ENGINE: Patched local path fallback to: {path}")
            patched = True
            break
            
    if not patched:
        print("⚠️ OCR ENGINE WARNING: Tesseract binary not detected on PATH or default directories. OCR processing will be bypassed.")

import os
import boto3
import pdfplumber
from io import BytesIO
from fastapi import HTTPException, status
from PIL import Image
import pytesseract

class PDFParsingEngine:
    """
    High-fidelity structural document parser with automated 
    non-blocking OCR image-to-text fallback perimeters.
    """
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "industryos-knowledge-vault")
        self.endpoint_url = os.getenv("AWS_ENDPOINT_URL", None)

        client_kwargs = {
            "service_name": "s3",
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "mock_key"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "mock_secret"),
            "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        }
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url

        self.s3_client = boto3.client(**client_kwargs)

        # 🪐 AUTOMATED PATH ALIGNMENT FOR WINDOWS SYSTEM DEVELOPERS
        # Binds the internal system execution path straight to our tesseract binary vault
        default_windows_tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(default_windows_tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = default_windows_tesseract_path
            self.ocr_available = True
            print("🧠 OCR MODULE INITIALIZATION: Local Tesseract binary linked successfully.")
        else:
            self.ocr_available = False
            print("⚠️ OCR MODULE WARN: Tesseract binary missing on host. Scanned PDF assets will bypass OCR loops.")

    def extract_structured_pdf_text(self, s3_key: str) -> str:
        """
        Processes document assets. If native programmatic vector text extraction 
        returns zero data footprints, automatically triggers the OCR engine fallback loop.
        """
        try:
            # Load asset from local fallback folder or cloud stream channel
            mock_path = os.path.join(os.getcwd(), "mock_s3_vault", s3_key)
            if os.path.exists(mock_path):
                with open(mock_path, "rb") as local_file:
                    raw_pdf_bytes = local_file.read()
            else:
                s3_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                raw_pdf_bytes = s3_object["Body"].read()
            
            extracted_content_accumulator = []
            is_scanned_document = False

            # 1. Tier 1 Pass: Programmatic Vector Layout Extraction Loop
            with pdfplumber.open(BytesIO(raw_pdf_bytes)) as pdf_canvas:
                for page_index, page_frame in enumerate(pdf_canvas.pages):
                    page_text = page_frame.extract_text(layout=True)
                    
                    if page_text and page_text.strip():
                        extracted_content_accumulator.append(
                            f"--- [STRUCTURED ASSET PAGE BOUNDARY: INDEX {page_index + 1}] ---\n"
                            f"{page_text}\n"
                        )
                    else:
                        # An empty page text block confirms a flattened page layout image
                        is_scanned_document = True
                        break

            # 2. Tier 2 Pass: Reactive Local Image OCR Fallback Engine Loop
            if is_scanned_document or len(extracted_content_accumulator) == 0:
                print("🚨 PARSER ENGINE: Zero character glyph data found. Activating OCR Fallback Canvas Loop...")
                
                if not self.ocr_available:
                    raise ValueError(
                        "Document file contains zero extractable text attributes, and local OCR framework "
                        "is offline. Please verify that Tesseract is installed at C:\\Program Files\\Tesseract-OCR."
                    )
                
                extracted_content_accumulator = [] # Reset buffer fresh
                
                with pdfplumber.open(BytesIO(raw_pdf_bytes)) as pdf_canvas:
                    for page_index, page_frame in enumerate(pdf_canvas.pages):
                        print(f"📸 OCR ENGINE: Rasterizing graphic page coordinates layout index {page_index + 1}...")
                        
                        # Render page vectors to high-definition PIL Image object context structures
                        # 150 DPI is the sweet spot: perfectly balancing recognition accuracy with high performance speed
                        page_image_sheet = page_frame.to_image(resolution=150).original
                        
                        # Process image bitmap pixels through local Tesseract neural layers
                        ocr_extracted_text = pytesseract.image_to_string(page_image_sheet)
                        
                        if ocr_extracted_text.strip():
                            extracted_content_accumulator.append(
                                f"--- [STRUCTURED ASSET PAGE BOUNDARY: INDEX {page_index + 1}] ---\n"
                                f"{ocr_extracted_text}\n"
                            )

            unified_document_payload = "".join(extracted_content_accumulator)
            
            if not unified_document_payload.strip():
                raise ValueError("OCR engine failed to identify any structural characters inside the target document image.")
                
            return unified_document_payload

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Parser infrastructure failed to extract content assets: {str(e)}"
            )

# Instantiate the centralized singleton driver asset instance
pdf_parser_service = PDFParsingEngine()