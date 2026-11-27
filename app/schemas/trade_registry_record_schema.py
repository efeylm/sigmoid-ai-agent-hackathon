from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# Ortak Alanlar
class TradeRegistryRecordBase(BaseModel):
    summary: Optional[str] = None
    risk_score: Optional[int] = 0
    details: Optional[Dict[str, Any]] = None  # JSON içeriği buraya map edilecek
    announcement_date: Optional[str] = None
    pdf_path: Optional[str] = None

# Kayıt Oluştururken (Service içinde kullanılır)
class TradeRegistryRecordCreate(TradeRegistryRecordBase):
    report_id: int

# API Response (Kullanıcıya dönerken)
class TradeRegistryRecordResponse(TradeRegistryRecordBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # ORM (SQLAlchemy) objesini Pydantic'e çevirir