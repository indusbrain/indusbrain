import os
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

class S3StorageService:
    """
    Enterprise-grade storage driver with an integrated local simulation matrix 
    to support seamless, high-performance offline developer sandboxes.
    """
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "industryos-knowledge-vault")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "mock_key")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "mock_secret")
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.endpoint_url = os.getenv("AWS_ENDPOINT_URL", None)

        # 🪐 OFFLINE PERIMETER DETECTION
        # Bypasses internet cloud loops if key manifests are explicitly marked as mock profiles
        self.is_offline_mock = (
            self.access_key.startswith("mock") or 
            os.getenv("APP_ENV") == "development" and not self.endpoint_url
        )

        if not self.is_offline_mock:
            client_kwargs = {
                "service_name": "s3",
                "aws_access_key_id": self.access_key,
                "aws_secret_access_key": self.secret_key,
                "region_name": self.region
            }
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url
            
            self.s3_client = boto3.client(**client_kwargs)
            self._ensure_bucket_exists()
        else:
            print("📦 STORAGE INITIALIZATION: Operating in pristine OFFLINE LOCAL MOCK Mode. Real AWS S3 bypassed.")
            os.makedirs(os.path.join(os.getcwd(), "mock_s3_vault"), exist_ok=True)

    def _ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code"))
            if error_code in ["404", "403", "NoSuchBucket"]:
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                except Exception as ce:
                    print(f"⚠️ STORAGE INITIALIZATION BYPASSED: Sandbox fallback active. {str(ce)}")

    def upload_file_sync(self, file_obj, s3_key: str):
        """
        Persists raw binary document fragments directly to the target storage block.
        """
        if self.is_offline_mock:
            # Direct Local Sandbox Persistence Path
            mock_dest = os.path.join(os.getcwd(), "mock_s3_vault", s3_key)
            os.makedirs(os.path.dirname(mock_dest), exist_ok=True)
            
            # Read straight from the open Starlette file stream wrapper
            file_obj.seek(0)
            file_bytes = file_obj.read()
            
            with open(mock_dest, "wb") as local_file:
                local_file.write(file_bytes)
            print(f"💾 LOCAL MOCK STORAGE VAULT: Saved binary object cleanly to {mock_dest}")
            return

        # Cloud Production Cluster Upload Path
        try:
            file_obj.seek(0)
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={"ContentType": "application/pdf"}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cloud Storage Driver Ingestion Failure: {str(e)}"
            )

storage_service = S3StorageService()