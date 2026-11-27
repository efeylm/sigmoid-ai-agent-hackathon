# app/agents/sicil_gazetesi/tools.py

from langchain_core.tools import tool
from playwright.sync_api import sync_playwright
from app.agents.sicil_gazetesi.scraper_engine import auth, search, view_announcement
import os
from concurrent.futures import ThreadPoolExecutor
import pytesseract
from pdf2image import convert_from_path
from pydantic import BaseModel, Field
from typing import Optional, List
from app.logger import logger

class ScraperInput(BaseModel):
    company_name: str = Field(description="Aranacak şirketin tam ünvanı")
    start_date: Optional[str] = Field(None, description="Başlangıç tarihi (gg/aa/yyyy) formatında")
    end_date: Optional[str] = Field(None, description="Bitiş tarihi (gg/aa/yyyy) formatında")

def _run_playwright_logic(company_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    logger.info(f"\n🚀 TOOL BAŞLATILIYOR (Playwright - Thread Mode): {company_name}")
    if start_date and end_date:
        logger.info(f"📅 Tarih Filtresi: {start_date} - {end_date}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 1. AUTH
            logger.info("🔑 Giriş fonksiyonu çağrılıyor...")
            is_logged_in = auth.login(page)
            if not is_logged_in:
                browser.close()
                return [] 
            
            # 2. SEARCH
            logger.info(f"🔍 Şirket aranıyor: {company_name}")
            search_results = search.search_company_title(page, company_name)
            
            city_name = None
            if isinstance(search_results, str):
                city_name = search_results
            elif isinstance(search_results, list) and len(search_results) > 0:
                item = search_results[0]
                city_name = item if isinstance(item, str) else item.get("tsm") or item.get("city")

            if not city_name:
                logger.error(f"🔥 HATA: Şehir bulunamadı.")
                browser.close()
                return []

            logger.info(f"🏙️ İşlem yapılacak şehir: {city_name}")

            pdf_paths_list = view_announcement.fill_and_submit_announcement_form(
                page, 
                city_name, 
                company_name, 
                start_date=start_date, 
                end_date=end_date      
            )
            
            browser.close()

            if pdf_paths_list and isinstance(pdf_paths_list, list) and len(pdf_paths_list) > 0:
                logger.info(f"✅ Toplam {len(pdf_paths_list)} PDF indirildi.")
                return pdf_paths_list
            else:
                logger.warning("❌ HATA veya UYARI: PDF listesi boş döndü (İlan bulunamamış olabilir).")
                return []

        except Exception as e:
            logger.error(f"🔥 KRİTİK PLAYWRIGHT HATASI: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            try:
                browser.close()
            except:
                pass
            return []

@tool(args_schema=ScraperInput)
def scrape_sicil_gazetesi(company_name: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Şirket ismini (ve opsiyonel tarih aralığını) kullanarak Sicil Gazetesi'ni tarar 
    ve bulunan ilanların PDF yollarını LİSTE olarak döner.
    """
    with ThreadPoolExecutor() as executor:
        future = executor.submit(_run_playwright_logic, company_name, start_date, end_date)
        return future.result()

@tool
def ocr_sicil_documents(pdf_path: str):
    """Tek bir PDF dosyasını alır ve metne çevirir."""
    logger.info(f"📖 OCR İşlemi: {pdf_path}")
    try:
        images = convert_from_path(pdf_path)
        full_text = ""
        for img in images:
            text = pytesseract.image_to_string(img, lang='tur')
            full_text += text + "\n\n"
        return full_text
    except Exception as e:
        logger.error(f"🔥 OCR Hatası ({pdf_path}): {e}")
        return ""