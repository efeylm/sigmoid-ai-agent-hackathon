from typing import List, Optional
from pydantic import BaseModel, Field

# --- Mevcut Modellerin ---
class KeyValue(BaseModel):
    key: str = Field(description="Bulunan başlık (Örn: 'Mersis Numarası', 'Eski Sermaye')")
    value: str = Field(description="Bu başlığın karşılığı olan değer")

class SicilAnalysisResult(BaseModel):
    """Tek bir sicil gazetesi ilanının analiz sonucu."""
    summary: str = Field(description="İlanın 1-2 cümlelik kısa ve net özeti.")
    details: List[KeyValue] = Field(description="Metinden çıkarılan yapılandırılmış veri listesi.")
    risk_score: Optional[int] = Field(description="İlanda riskli veya kritik bir durum varsa 1-10 arası puan (10 çok kritik).", default=0)

# --- YENİ EKLENEN KISIM ---
class SicilBatchResponse(BaseModel):
    """Birden fazla PDF analizinin toplu sonucu."""
    status: str = Field(description="İşlem durumu (success/error)")
    company_name: str = Field(description="Aranan şirket adı")
    total_found: int = Field(description="Bulunan ve indirilen ilan sayısı")
    results: List[SicilAnalysisResult] = Field(description="Her bir PDF için üretilen analiz sonuçları listesi")