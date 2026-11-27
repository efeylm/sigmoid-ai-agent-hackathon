# app/agents/resmi_gazete/adapters.py
from typing import List, Dict, Any
from .schemas import TenderBanItem

def adapt_tender_ban_results(raw_data: List[Dict[str, Any]], company_name: str) -> List[TenderBanItem]:
    """
    DB sonuçlarını standart TenderBanItem formatına dönüştürür.
    """
    standardized = []
    
    for item in raw_data:
        std_item = TenderBanItem(
            banned_record_no=item.get("banned_record_no"),
            tender_reg_no=item.get("tender_reg_no"),
            decision_ministry=item.get("decision_ministry"),
            authority_name=item.get("authority_name"),
            authority_address=item.get("authority_address"),
            authority_city=item.get("authority_city"),
            entity_type=item.get("entity_type"),
            banned_name=item.get("banned_name"),
            banned_tc=item.get("banned_tc"),
            banned_tax_id=item.get("banned_tax_id"),
            banned_address=item.get("banned_address"),
            legal_basis=item.get("legal_basis"),
            ban_scope=item.get("ban_scope"),
            ban_duration=item.get("ban_duration"),
            ban_reason=item.get("ban_reason"),
            gazette_date=item.get("gazette_date"),
            gazette_no=item.get("gazette_no"),
            source_url=item.get("source_url")
        )
        standardized.append(std_item)
    
    return standardized