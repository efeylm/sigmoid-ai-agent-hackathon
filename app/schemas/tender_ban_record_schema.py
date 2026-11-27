# TenderBanRecord Pydantic schemas
from pydantic import BaseModel
from typing import Optional

class TenderBanRecordBase(BaseModel):
    report_id: Optional[int] = None
    
    # Ana Tanımlayıcılar
    banned_record_no: Optional[str] = None
    tender_reg_no: Optional[str] = None
    decision_ministry: Optional[str] = None
    
    # İdare Bilgileri
    authority_name: Optional[str] = None
    authority_address: Optional[str] = None
    authority_postal_code: Optional[str] = None
    authority_city: Optional[str] = None
    authority_district: Optional[str] = None
    authority_phone_kep: Optional[str] = None
    authority_email: Optional[str] = None
    
    # Yasaklı Bilgileri
    entity_type: Optional[str] = None
    banned_name: Optional[str] = None
    banned_tc: Optional[str] = None
    banned_tax_id: Optional[str] = None
    banned_passport_no: Optional[str] = None
    banned_address: Optional[str] = None
    
    # Ortak Bilgileri
    partner_name: Optional[str] = None
    partner_city: Optional[str] = None
    partner_district: Optional[str] = None
    partner_postal_code: Optional[str] = None
    partner_address: Optional[str] = None
    partnership_info: Optional[str] = None
    
    # Yasak Detayları
    legal_basis: Optional[str] = None
    ban_scope: Optional[str] = None
    ban_duration: Optional[str] = None
    ban_reason: Optional[str] = None
    
    # Metadata
    gazette_date: Optional[str] = None
    gazette_no: Optional[str] = None
    content: Optional[str] = None

class TenderBanRecordCreate(TenderBanRecordBase):
    pass

class TenderBanRecordResponse(TenderBanRecordBase):
    id: int

    class Config:
        from_attributes = True
