from pydantic import BaseModel
from datetime import datetime
from app.models.document import DocumentStatus

class DocumentResponse(BaseModel):
    id: int
    filename: str
    s3_key: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    created_at: datetime

    class Config:
        from_attributes = True