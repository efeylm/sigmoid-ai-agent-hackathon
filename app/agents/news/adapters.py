# app/agents/news/adapters.py

from typing import List, Dict, Any
from .schemas import NewsItem

def adapt_tavily_results(tavily_output: Dict[str, Any], company_name: str) -> List[NewsItem]:
    items = tavily_output.get("news_items", [])
    standardized = []
    
    for item in items:
        std_item = NewsItem(
            title=item.get("baslik", ""),
            url=item.get("link", ""),
            content=item.get("ozet", ""),
            sentiment=item.get("duygu_analizi", "NÖTR"),
            image_path=item.get("gorsel_yolu"),
            published_date=item.get("tarih"), # Tavily bazen tarih dönmez, kontrol et
            source_provider="TAVILY"
        )
        standardized.append(std_item)
    return standardized

def adapt_google_results(google_output: List[Dict[str, Any]], company_name: str) -> List[NewsItem]:
    standardized = []
    for item in google_output:
        std_item = NewsItem(
            title=item.get("baslik", ""),
            url=item.get("web_linki", ""),
            content=item.get("text_metni", ""),
            sentiment=item.get("kategorisi", "NÖTR"),
            image_path=item.get("jpeg_goruntusu"),
            published_date=item.get("tarih"),
            source_provider="GOOGLE"
        )
        standardized.append(std_item)
    return standardized