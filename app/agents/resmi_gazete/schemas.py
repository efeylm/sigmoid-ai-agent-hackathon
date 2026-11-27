# app/agents/resmi_gazete/schemas.py
from pydantic import BaseModel
from typing import Optional, List

class TenderBanItem(BaseModel):
    """Tek bir ihale yasağı kaydı"""
    banned_record_no: Optional[str] = None
    tender_reg_no: Optional[str] = None
    decision_ministry: Optional[str] = None
    authority_name: Optional[str] = None
    authority_address: Optional[str] = None
    authority_city: Optional[str] = None
    entity_type: Optional[str] = None
    banned_name: Optional[str] = None
    banned_tc: Optional[str] = None
    banned_tax_id: Optional[str] = None
    banned_address: Optional[str] = None
    legal_basis: Optional[str] = None
    ban_scope: Optional[str] = None
    ban_duration: Optional[str] = None
    ban_reason: Optional[str] = None
    gazette_date: Optional[str] = None
    gazette_no: Optional[str] = None
    source_url: Optional[str] = None

class TenderBanResponse(BaseModel):
    """İhale yasağı arama yanıtı"""
    company: str
    total_results: int
    results: List[TenderBanItem]