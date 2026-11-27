# app/agents/news/schemas.py

from pydantic import BaseModel
from typing import Optional, List

# Arama İsteği Modeli
class NewsSearchRequest(BaseModel):
    company_name: str
    start_date: str # DD/MM/YYYY
    end_date: str   # DD/MM/YYYY
    provider: str = "TAVILY" # "TAVILY" veya "GOOGLE"

# Standart Haber Çıktısı (Tekil)
class NewsItem(BaseModel):
    title: str
    url: str
    content: str
    sentiment: str
    image_path: Optional[str] = None
    published_date: Optional[str] = None
    source_provider: str

# API Dönüş Modeli
class NewsResponse(BaseModel):
    company: str
    total_results: int
    results: List[NewsItem]