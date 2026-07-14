import os
import boto3
import pdfplumber
from io import BytesIO
from fastapi import HTTPException, status

class PDFParsingEngine:
    """
    High-fidelity structural document parser. Extracts text blocks 
    and handles layout coordinates without scrambling multi-column or tabular metrics.
    """
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "industryos-knowledge-vault")
        
        # Determine if we have a local container fallback url
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

    def extract_structured_pdf_text(self, s3_key: str) -> str:
        """
        Downloads target asset file binary data from storage vault 
        and extracts layout-isolated string contents cleanly.
        """
        try:
            # Check if operating in local file fallback mode
            mock_path = os.path.join(os.getcwd(), "mock_s3_vault", s3_key)
            
            if os.path.exists(mock_path):
                print(f"💾 PARSER CORE: Loading asset via local fallback repository vault: {mock_path}")
                with open(mock_path, "rb") as local_file:
                    raw_pdf_bytes = local_file.read()
            else:
                # Standard Cloud Stream Retrieval Route
                s3_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                raw_pdf_bytes = s3_object["Body"].read()
            
            extracted_content_accumulator = []

            # Open binary envelope inside our spatial canvas analyzer engine
            with pdfplumber.open(BytesIO(raw_pdf_bytes)) as pdf_canvas:
                for page_index, page_frame in enumerate(pdf_canvas.pages):
                    # Extract text using structural layout preservation directives
                    page_text = page_frame.extract_text(layout=True)
                    
                    if page_text:
                        extracted_content_accumulator.append(
                            f"--- [STRUCTURED ASSET PAGE BOUNDARY: INDEX {page_index + 1}] ---\n"
                            f"{page_text}\n"
                        )
            
            unified_document_payload = "".join(extracted_content_accumulator)
            
            if not unified_document_payload.strip():
                raise ValueError("Document file contains zero extractable text attributes or structural characters.")
                
            return unified_document_payload

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Parser infrastructure failed to extract content assets: {str(e)}"
            )

# Instantiate the singleton service driver instance
pdf_parser_service = PDFParsingEngine()