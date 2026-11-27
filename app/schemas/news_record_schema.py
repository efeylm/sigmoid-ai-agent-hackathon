# NewsRecord Pydantic schemas
from pydantic import BaseModel
from typing import Optional

class NewsRecordBase(BaseModel):
    source_url: Optional[str] = None
    headline: Optional[str] = None
    content: Optional[str] = None
    publication_date: Optional[str] = None
    sentiment: Optional[str] = None
    image_path: Optional[str] = None
    report_id: Optional[int] = None

class NewsRecordCreate(NewsRecordBase):
    pass

class NewsRecordResponse(NewsRecordBase):
    id: int

    class Config:
        from_attributes = True
