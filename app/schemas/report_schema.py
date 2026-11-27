# Report Pydantic schemas
# Data Transfer Objects (DTOs) for report data validation
# Request and response models for report endpoints
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Import related schemas
from app.schemas.news_record_schema import NewsRecordResponse
from app.schemas.trade_registry_record_schema import TradeRegistryRecordResponse
from app.schemas.tender_ban_record_schema import TenderBanRecordResponse
from app.schemas.company_schema import CompanyResponse
from app.schemas.query_schema import QueryResponse

class ReportBase(BaseModel):
    final_summary: Optional[str] = None
    query_id: Optional[int] = None
    company_id: Optional[int] = None

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    created_at: Optional[datetime] = None
    
    # Relationships
    query: Optional[QueryResponse] = None
    company: Optional[CompanyResponse] = None
    
    news_records: List[NewsRecordResponse] = []
    registry_records: List[TradeRegistryRecordResponse] = []
    ban_records: List[TenderBanRecordResponse] = []

    class Config:
        from_attributes = True
