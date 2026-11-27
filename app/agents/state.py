from typing import TypedDict, Optional, List, Dict, Any


#EY BURAYI OKUYAN KİŞİ BU KOD SÜREÇ BOYUNCA TAŞINAN ŞEYLERİN BİLGİSİNİ TUTUYO.
#TODO Emirhan ve Efe burayı kendi formatınıza göre dolduracaksınız
class MasterState(TypedDict):
    # --- GİRDİLER ---
    company_name: str
    request_id: str  # Loglama ve DB takibi için ID. İleride kullancaz
    start_date: Optional[str]
    end_date: Optional[str]

    sicil_data: List[Dict[str, Any]] 
    # Henüz yapılmadı (TODO)
    resmi_gazete_data: Optional[List[Any]]
    web_search_data: Optional[List[Any]]
    
    final_report: Optional[str]
    
    errors: List[str]