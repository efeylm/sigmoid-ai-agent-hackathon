import json
import logging
import time
import httpx
from enum import Enum
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from app.llm import get_chat_llm
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from sqlalchemy.orm import Session

from app.config import settings
from app.agents.news.scrapers.tavily_client import TavilyScraper
from app.agents.news.scrapers.google_client import GoogleScraper
from app.agents.sicil_gazetesi.workflow import sicil_app

from app.agents.resmi_gazete.client import TenderBanClient
from app.models.tender_ban_record import TenderBanRecord

from app.models.company import Company
from app.models.report import Report
from app.models.news_record import NewsRecord
from app.models.trade_registry_record import TradeRegistryRecord


class SearchAgentType(str, Enum):
    TAVILY = "TAVILY"
    GOOGLE = "GOOGLE"


@tool
def search_tavily(company_name: str, start_date: str, end_date: str):
    """
    Searches for news about a company using Tavily.
    Args:
        company_name: Name of the company.
        start_date: Start date in DD/MM/YYYY format.
        end_date: End date in DD/MM/YYYY format.
    """
    scraper = TavilyScraper()
    return scraper.search(company_name, start_date, end_date)


@tool
def search_google(company_name: str, start_date: str, end_date: str):
    """
    Searches for news about a company using Google News.
    Args:
        company_name: Name of the company.
        start_date: Start date in DD/MM/YYYY format.
        end_date: End date in DD/MM/YYYY format.
    """
    scraper = GoogleScraper()
    return scraper.search(company_name, start_date, end_date)


@tool
async def search_sicil_gazetesi(company_name: str, start_date: str, end_date: str):
    """
    Searches for official trade registry records (Sicil Gazetesi) for a company.
    Args:
        company_name: Name of the company.
        start_date: Start date in DD/MM/YYYY format.
        end_date: End date in DD/MM/YYYY format.
    """
    input_state = {
        "company_name": company_name,
        "start_date": start_date,
        "end_date": end_date,
        "pdf_paths": [],
        "ocr_results": [],
        "analysis_results": []
    }
    result = await sicil_app.ainvoke(input_state)
    if result.get("access_failed"):
        # Surface access failures so the report says "could not be queried", not "no records"
        raise RuntimeError(result.get("error") or "Sicil Gazetesi sorgulanamadı")
    analysis_results = result.get("analysis_results", [])
    
    serialized_results = []
    for item in analysis_results:
        if hasattr(item, "model_dump"):
            serialized_results.append(item.model_dump())
        elif hasattr(item, "dict"):
            serialized_results.append(item.dict())
        else:
            serialized_results.append(item)
            
    return serialized_results

# Yeni tool tanımı (@tool decorator ile)
@tool
def search_tender_bans(company_name: str, start_date: str, end_date: str):
    """
    Resmi Gazete'de yayınlanan ihale yasaklıları listesinden şirket adına göre arama yapar.
    Args:
        company_name: Aranacak şirketin adı veya ünvanı
        start_date: Başlangıç tarihi (DD/MM/YYYY formatında)
        end_date: Bitiş tarihi (DD/MM/YYYY formatında)
    """
    client = TenderBanClient()
    return client.search(company_name, start_date, end_date)


logger = logging.getLogger("app") 

class ReportAgent:
    def __init__(self, db: Session):
        self.db = db
        
        # Log LLM configuration
        logger.info("🤖 ReportAgent başlatılıyor...")
        logger.info(f"   Model: {settings.OPENAI_MODEL_NAME}")
        logger.info(f"   Base URL: {settings.OPENAI_BASE_URL}")
        logger.info(f"   Timeout: 300s (read), 60s (connect)")
        
        self.llm = get_chat_llm(
            temperature=0,
            max_tokens=10000,
            timeout=httpx.Timeout(300.0, connect=60.0),
            max_retries=3,
        )
        self.tools = [search_tavily, search_google, search_sicil_gazetesi, search_tender_bans]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        logger.info(f"   Tools: {[t.name for t in self.tools]}")
        logger.info("✅ ReportAgent hazır")

    def _get_or_create_company(self, company_name: str) -> Company:
        """Get existing company or create new one"""
        company = self.db.query(Company).filter(Company.name == company_name).first()
        if not company:
            logger.info(f"🆕 Creating new company: {company_name}")
            company = Company(name=company_name)
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
            logger.info(f"✅ Company created with ID: {company.id}")
        else:
            logger.info(f"ℹ️ Found existing company: {company.id}")
        return company

    def _create_report(self, company_id: int) -> Report:
        """Create a new report record"""
        report = Report(
            company_id=company_id,
            status="PROCESSING",
            content="Rapor oluşturuluyor..."
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        logger.info(f"✅ Report created with ID: {report.id} (Status: PROCESSING)")
        return report

    def _save_news_records(self, news_data: List[Dict[str, Any]], report_id: int) -> int:
        """
        Save news records to database.
        Handles both Tavily format (baslik, link, ozet) and standard format (title, url, content).
        Returns count of saved records.
        """
        saved_count = 0
        
        if not news_data or not isinstance(news_data, list):
            return saved_count
        
        for item in news_data:
            try:
                # Handle Tavily format (Turkish keys) or standard format (English keys)
                url = item.get("link") or item.get("url")
                title = item.get("baslik") or item.get("title")
                content = item.get("ozet") or item.get("content")
                sentiment = item.get("duygu_analizi") or item.get("sentiment")
                image_path = item.get("gorsel_yolu") or item.get("image_path")
                published_date = item.get("tarih") or item.get("published_date")
                
                if not url:
                    continue
                
                # Check for duplicate by URL
                existing = self.db.query(NewsRecord).filter(
                    NewsRecord.report_id == report_id,
                    NewsRecord.source_url == url
                ).first()
                
                if not existing:
                    record = NewsRecord(
                        report_id=report_id,
                        source_url=url,
                        headline=title,
                        content=content,
                        publication_date=published_date,
                        sentiment=sentiment,
                        image_path=image_path
                    )
                    self.db.add(record)
                    saved_count += 1
            except Exception as e:
                logger.error(f"⚠️ News kayıt hatası: {e}")
                continue
        
        if saved_count > 0:
            self.db.commit()
            logger.info(f"💾 {saved_count} haber kaydedildi.")
        
        return saved_count


    def _save_sicil_records(self, sicil_data: List[Dict[str, Any]], report_id: int) -> int:
        """
        Save trade registry records to database.
        Returns count of saved records.
        """
        logger.info(f"💾 Saving sicil records... Count: {len(sicil_data)}")
        saved_count = 0
        
        if not sicil_data or not isinstance(sicil_data, list):
            logger.warning("⚠️ No sicil data to save or invalid format.")
            return saved_count
        
        for item in sicil_data:
            try:
                logger.info(f"Processing sicil item: {item.get('summary')[:50] if item.get('summary') else 'No summary'}")
                raw_details = item.get("details", [])
                
                if isinstance(raw_details, list):
                    details_json = {}
                    for detail in raw_details:
                        if isinstance(detail, dict):
                            key = detail.get("key")
                            value = detail.get("value")
                            if key:
                                details_json[key] = value
                else:
                    details_json = raw_details if isinstance(raw_details, dict) else {}
                
                announcement_date = details_json.get("İlan Tarihi") or details_json.get("Tarih")
                
                record = TradeRegistryRecord(
                    report_id=report_id,
                    summary=item.get("summary"),
                    risk_score=item.get("risk_score", 0),
                    details=details_json,
                    announcement_date=announcement_date
                )
                self.db.add(record)
                saved_count += 1
            except Exception as e:
                logger.error(f"🔥 Sicil save error: {e}", exc_info=True)
                continue
        
        if saved_count > 0:
            self.db.commit()
            logger.info(f"✅ {saved_count} sicil records committed to DB.")
        else:
            logger.warning("⚠️ No sicil records were saved.")
        
        return saved_count

    def _extract_news_from_tool_output(self, tool_output: Any) -> List[Dict[str, Any]]:
        """
        Extract news items from tool output.
        Handles both dict format (Tavily: {news_items: [...]}) and list format.
        """
        if isinstance(tool_output, dict):
            # Tavily format: {"summary": "...", "news_items": [...]}
            return tool_output.get("news_items", [])
        elif isinstance(tool_output, list):
            return tool_output
        return []

    # AI-generated: Format sicil data to emphasize details field for LLM
    def _format_sicil_for_llm(self, sicil_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transforms sicil data to emphasize 'details' field for LLM report generation.
        Converts details from list of KeyValue to flat dict and removes summary.
        """
        formatted_data = []
        
        for idx, item in enumerate(sicil_data):
            # Extract details - can be list of KeyValue or already a dict
            raw_details = item.get("details", [])
            
            # Convert list of {key, value} to flat dict
            if isinstance(raw_details, list):
                details_dict = {}
                for detail in raw_details:
                    if isinstance(detail, dict):
                        key = detail.get("key")
                        value = detail.get("value")
                        if key:
                            details_dict[key] = value
            else:
                details_dict = raw_details if isinstance(raw_details, dict) else {}
            
            # Create formatted record with details as primary data
            formatted_record = {
                "kayit_no": idx + 1,
                "risk_score": item.get("risk_score", 0),
                "details": details_dict  # Flat dict with all key-value pairs
            }
            
            formatted_data.append(formatted_record)
        
        return formatted_data

    def _format_news_for_llm(self, news_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format news data for LLM, including image paths in markdown format.
        Image paths from DB are like: haber_gorselleri_tavily/image123.jpg
        """
        formatted_news = []
    
        for idx, item in enumerate(news_data):
            url = item.get("link") or item.get("url")
            title = item.get("baslik") or item.get("title")
            content = item.get("ozet") or item.get("content")
            sentiment = item.get("duygu_analizi") or item.get("sentiment")
            image_path = item.get("gorsel_yolu") or item.get("image_path")
            published_date = item.get("tarih") or item.get("published_date")
        
            formatted_item = {
                "sira_no": idx + 1,
                "baslik": title,
                "ozet": content,
                "kaynak_url": url,
                "tarih": published_date,
                "duygu": sentiment
            }
        
            # Add image if available - keep the path as is (haber_gorselleri_tavily/...)
            if image_path:
                formatted_item["gorsel"] = image_path
            
            formatted_news.append(formatted_item)
    
        return formatted_news

    # AI-generated: Format tender ban data for LLM report generation
    def _format_tender_bans_for_llm(self, ban_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        İhale yasaklı verilerini LLM için tablo formatına hazırlar.
        Null olmayan tüm alanları Türkçe etiketlerle döndürür.
        """
        formatted_data = []
        
        # Alan adları mapping (DB key -> Türkçe label)
        field_labels = {
            "banned_record_no": "Yasaklı Kayıt No",
            "tender_reg_no": "İhale Kayıt No",
            "decision_ministry": "Karar Veren Kurum",
            "authority_name": "İdare Adı",
            "authority_address": "İdare Adresi",
            "authority_city": "İdare İli",
            "authority_district": "İdare İlçesi",
            "authority_phone_kep": "İdare Telefon",
            "entity_type": "Kişi Türü",
            "banned_name": "Yasaklı Adı/Ünvanı",
            "banned_tc": "TC Kimlik No",
            "banned_tax_id": "Vergi Kimlik No",
            "banned_address": "Yasaklı Adresi",
            "legal_basis": "Kanun Dayanağı",
            "ban_scope": "Yasak Kapsamı",
            "ban_duration": "Yasak Süresi",
            "ban_reason": "Yasak Gerekçesi",
            "gazette_date": "Gazete Tarihi",
            "gazette_no": "Gazete No",
            "source_url": "Kaynak URL"
        }
        
        for idx, item in enumerate(ban_data):
            record = {"sira_no": idx + 1}
            
            # Sadece null olmayan alanları ekle
            for key, label in field_labels.items():
                value = item.get(key)
                if value and str(value).strip() and str(value).strip() != "null":
                    record[label] = value
            
            formatted_data.append(record)
        
        return formatted_data

    
    async def generate_report(
        self, 
        company_name: str, 
        start_date: str, 
        end_date: str, 
        agent_type: SearchAgentType
    ) -> Dict[str, Any]:
        """
        Generate report and save all data to database.
        Returns dict with report_id, report_content, news_count, sicil_count.
        """
        
        logger.info("=" * 60)
        logger.info(f"🚀 RAPOR OLUŞTURMA BAŞLADI")
        logger.info(f"   Şirket: {company_name}")
        logger.info(f"   Tarih Aralığı: {start_date} - {end_date}")
        logger.info(f"   Agent Tipi: {agent_type.value}")
        logger.info("=" * 60)
        
        company = self._get_or_create_company(company_name)
        report = self._create_report(company.id)
        
        news_count = 0
        sicil_count = 0
        news_raw_data = []
        sicil_raw_data = []
        
        try:
            # AI-generated: Updated system prompt to use details field and table format
            system_prompt = f"""Profesyonel bir mali istihbarat raporlayıcısısın.
            Görevin, '{company_name}' şirketi için kapsamlı bir rapor oluşturmaktır.

            **KRİTİK TALİMAT - MUTLAKA UYULMALI:**
            Aşağıdaki 3 aracın HEPSİNİ çağırmalısın. Hiçbirini ATLAMA!
            1. '{agent_type.value}' arama aracı (Web haberleri için) - ZORUNLU
            2. 'search_sicil_gazetesi' aracı (Resmi şirket kayıtları için) - ZORUNLU  
            3. 'search_tender_bans' aracı (İhale yasaklıları için) - ZORUNLU

            ⚠️ Bu 3 araçtan herhangi birini çağırmazsan rapor EKSİK kalır!

            ADIMLAR:
            1. Belirtilen web arama aracını ({agent_type.value}) kullanarak verileri topla.
            2. 'search_sicil_gazetesi' aracını kullanarak resmi kayıtları topla.
            3. 'search_tender_bans' aracını kullanarak ihale yasaklılarını kontrol et.
            4. Tüm kaynaklardan gelen verileri analiz et ve sentezle.
            5. Aşağıdaki başlıkları içeren detaylı bir rapor yaz:
            - Yönetici Özeti
            - Web Haberleri Analizi (Önemli gelişmeler, riskler)
            - Sicil Gazetesi Verileri (Resmi değişiklikler, duyurular)
            - İhale Yasaklıları (Kamu ihalelerinden men durumu)
            - Risk Değerlendirmesi
                        
            SİCİL GAZETESİ VERİLERİ İÇİN ZORUNLU FORMAT:
            - Her sicil kaydı için 'details' alanındaki yapılandırılmış verileri kullan, 'summary' alanını KULLANMA.
            - 'details' alanı şu bilgileri içerir: Şirket Unvanı, MERSİS No, Ticaret Sicil/Dosya No, İlan Sıra No, İlan Konusu, Tescil Tarihi, vb.
            - Her sicil kaydını aşağıdaki Markdown tablo formatında göster:
            
            ### Sicil Gazetesi Kaydı #[numara]
            
            | Alan                      | Değer                                    |
            |---------------------------|------------------------------------------|
            | Şirket Unvanı             | [değer]                                  |
            | MERSİS No                 | [değer]                                  |
            | Ticaret Sicil/Dosya No    | [değer]                                  |
            | İlan Konusu               | [değer]                                  |
            | Tescil Tarihi             | [değer]                                  |
            | [diğer alanlar...]        | [değer]                                  |
            
            - Tablo kolonlarını hizalı tut: sol kolon 25 karakter, sağ kolon 40 karakter genişliğinde olsun.
            - Tüm 'details' içindeki key-value çiftlerini tabloya ekle, hiçbirini atlama.
            
            WEB HABERLERİ İÇİN ZORUNLU FORMAT:
            - Her haber için numaralandırılmış başlık kullan (### 1. Haber Başlığı)
            - Haber detaylarını paragraf olarak yaz
            - **ÖNEMLİ**: Eğer haberde 'gorsel' alanı varsa, haberin hemen altına şu formatta ekle:
            ![Haber Görseli](GORSEL_YOLU)
            - Sentiment sütununda ilgili haberin OLUMLU-OLUMSUZ-NÖTR olduğu bilgisi mevcut. Bu bilgiyi kullanmak zorundasın. Buradaki bilgi ilgili haberin sentiment analizinin sonucudur. Bu bilgiyi kullan.
            - Source_url sütununda ilgili haberin kaynağının URL'i mevcut. Bu bilgiyi kullanmak zorundasın. Bu bilgi sayesinde haberin kaynağının URL'i kullanılabilir.
            - Örnek:
            ### 1. AXA Türkiye CEO'su Açıklama Yaptı
            
            AXA Türkiye CEO'su sektörle ilgili önemli açıklamalarda bulundu...
            
            ![Haber Görseli](/path/to/image.jpg)
            
            İHALE YASAKLILARI İÇİN ZORUNLU FORMAT:
            - 'search_tender_bans' aracını MUTLAKA kullan.
            - Bu araç, Resmi Gazete'de yayınlanan ihale yasaklılarını veritabanından sorgular.
            - Gelen veride her kayıt için 'sira_no' ve diğer alanlar Türkçe etiketlerle gelir.
            - Her ihale yasağı kaydını aşağıdaki Markdown tablo formatında göster:
            
            ### İhale Yasaklıları
            
            ### İhale Yasağı Kaydı #[sira_no]

            | Alan                  | Değer                                              |
            |-----------------------|----------------------------------------------------|
            | [Alan Adı]            | [Değer]                                            |
            | [Alan Adı]            | [Değer]                                            |
            | ...                   | ...                                                |
            
            - **ÖNEMLİ**: Gelen verideki TÜM alanları tabloya ekle, hiçbirini atlama.
            - Her kayıt için ayrı bir tablo oluştur.
            - HABERLER İÇİN'kaynak Url' alanı varsa tıklanabilir link olarak ekle: [Kaynak](URL)
            - HABERLER İÇİN sentiment analizi unutma. Her bir haber için sentiment analizinin sonucunu kullan. Pozitif, negatif veya nötr olabilir. Bu bilgiyi kullanmak zorundasın.
            - **KRİTİK**: Gelen TÜM kayıtları (sira_no: 1, 2, 3, ..., N) göster, hiçbir kaydı atlama!
            - Kayıt sayısı ne olursa olsun (3, 11, 50, 100) HEPSİNİ listele!
            - Her kayıt için ayrı bir tablo oluştur: "### İhale Yasağı Kaydı #1", "#2", "#3", ..., "#N"
            - Eğer yasaklı ilan bulunamazsa: "Aranan şirket için kamu ihale yasağı kaydı bulunamadı." yaz.
            
            
            ÖNEMLİ:
            - Raporu TAMAMEN TÜRKÇE yaz.
            - Eğer bir kaynaktan veri gelmezse, raporda "Veri bulunamadı" olarak belirt.
            - Markdown formatı kullan.
            - Tutarlı boşluk ve hizalama kullan (sağ ve sol kenar boşlukları eşit olmalı).
            - Haberler için sentiment analizinin sonucunu kullan.
            - Her haber için source_url sütununda ilgili haberin kaynağının URL'i mevcut. Bu bilgiyi kullanmak zorundasın. Bu bilgi sayesinde haberin kaynağının URL'i kullanılabilir.
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"'{company_name}' için {start_date} - {end_date} tarihleri arasında rapor oluştur. Web araması için {agent_type.value} kullan.")
            ]

            # DEBUG: Log message sizes before first LLM call
            logger.info("-" * 40)
            logger.info("📊 İLK LLM ÇAĞRISI ÖNCESİ - MESAJ BİLGİLERİ:")
            total_chars = sum(len(str(m.content)) for m in messages)
            logger.info(f"   Toplam mesaj sayısı: {len(messages)}")
            logger.info(f"   Toplam karakter sayısı: {total_chars}")
            logger.info(f"   System prompt uzunluğu: {len(system_prompt)} karakter")
            logger.info("-" * 40)
            
            logger.info("🔄 İlk LLM çağrısı başlıyor (tool seçimi için)...")
            llm_start_time = time.time()
            
            try:
                ai_msg = await self.llm_with_tools.ainvoke(messages)
                llm_elapsed = time.time() - llm_start_time
                logger.info(f"✅ İlk LLM çağrısı tamamlandı ({llm_elapsed:.2f} saniye)")
            except Exception as llm_error:
                llm_elapsed = time.time() - llm_start_time
                logger.error(f"❌ İLK LLM ÇAĞRISI BAŞARISIZ! ({llm_elapsed:.2f} saniye)")
                logger.error(f"   Hata tipi: {type(llm_error).__name__}")
                logger.error(f"   Hata mesajı: {str(llm_error)}")
                if hasattr(llm_error, 'response'):
                    logger.error(f"   Response: {llm_error.response}")
                raise
            
            messages.append(ai_msg)
            
            # DEBUG: Log tool calls
            if ai_msg.tool_calls:
                logger.info(f"🔧 LLM {len(ai_msg.tool_calls)} adet tool çağrısı istedi:")
                for i, tc in enumerate(ai_msg.tool_calls):
                    logger.info(f"   [{i+1}] Tool: {tc['name']}, Args: {tc['args']}")
            else:
                logger.warning("⚠️ LLM hiç tool çağrısı istemedi!")

            if ai_msg.tool_calls:
                logger.info("-" * 40)
                logger.info("🔧 TOOL ÇAĞRILARI BAŞLIYOR")
                logger.info("-" * 40)
                
                for tool_idx, tool_call in enumerate(ai_msg.tool_calls):
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    logger.info(f"\n>>> TOOL [{tool_idx+1}/{len(ai_msg.tool_calls)}]: {tool_name}")
                    logger.info(f"    Args: {tool_args}")
                    
                    tool_output = "Tool call failed or unknown."
                    tool_error_msg = None
                    
                    if tool_name == "search_tavily":
                        logger.info(f"⏳ {tool_name} çalıştırılıyor...")
                        start_time = time.time()
                        try:
                            tool_output = search_tavily.invoke(tool_args)
                            elapsed_time = time.time() - start_time
                            logger.info(f"✅ {tool_name} tamamlandı ({elapsed_time:.2f} saniye)")
                        except Exception as tool_error:
                            elapsed_time = time.time() - start_time
                            logger.error(f"❌ {tool_name} BAŞARISIZ! ({elapsed_time:.2f} saniye)")
                            logger.error(f"   Hata: {tool_error}")
                            # Keep going with the other sources instead of failing the whole report
                            tool_error_msg = str(tool_error)
                            tool_output = []
                        
                        raw_news = self._extract_news_from_tool_output(tool_output)
                        news_raw_data.extend(raw_news)
                        logger.info(f"📰 {len(raw_news)} adet haber çıkarıldı")
                        tool_output = self._format_news_for_llm(raw_news)
                        
                        # Log output size
                        output_json = json.dumps(tool_output, default=str, ensure_ascii=False)
                        logger.info(f"📊 Tool çıktı boyutu: {len(output_json)} karakter")

                    elif tool_name == "search_google":
                        logger.info(f"⏳ {tool_name} çalıştırılıyor...")
                        start_time = time.time()
                        try:
                            tool_output = search_google.invoke(tool_args)
                            elapsed_time = time.time() - start_time
                            logger.info(f"✅ {tool_name} tamamlandı ({elapsed_time:.2f} saniye)")
                        except Exception as tool_error:
                            elapsed_time = time.time() - start_time
                            logger.error(f"❌ {tool_name} BAŞARISIZ! ({elapsed_time:.2f} saniye)")
                            logger.error(f"   Hata: {tool_error}")
                            # Keep going with the other sources instead of failing the whole report
                            tool_error_msg = str(tool_error)
                            tool_output = []
                        
                        raw_news = self._extract_news_from_tool_output(tool_output)
                        news_raw_data.extend(raw_news)
                        logger.info(f"📰 {len(raw_news)} adet haber çıkarıldı")
                        tool_output = self._format_news_for_llm(raw_news)
                        
                        # Log output size
                        output_json = json.dumps(tool_output, default=str, ensure_ascii=False)
                        logger.info(f"📊 Tool çıktı boyutu: {len(output_json)} karakter")
                        
                    elif tool_name.startswith("search_sicil"):
                        logger.info(f"⏳ {tool_name} çalıştırılıyor...")
                        start_time = time.time()
                        try:
                            tool_output = await search_sicil_gazetesi.ainvoke(tool_args)
                            elapsed_time = time.time() - start_time
                            logger.info(f"✅ {tool_name} tamamlandı ({elapsed_time:.2f} saniye)")
                        except Exception as tool_error:
                            elapsed_time = time.time() - start_time
                            logger.error(f"❌ {tool_name} BAŞARISIZ! ({elapsed_time:.2f} saniye)")
                            logger.error(f"   Hata: {tool_error}")
                            # Keep going with the other sources instead of failing the whole report
                            tool_error_msg = str(tool_error)
                            tool_output = []
                        
                        sicil_raw_data = tool_output if isinstance(tool_output, list) else []
                        logger.info(f"📋 {len(sicil_raw_data)} adet sicil kaydı çıkarıldı")
                        # AI-generated: Format sicil data to emphasize details for LLM
                        tool_output = self._format_sicil_for_llm(sicil_raw_data)
                        
                        # Log output size
                        output_json = json.dumps(tool_output, default=str, ensure_ascii=False)
                        logger.info(f"📊 Tool çıktı boyutu: {len(output_json)} karakter")
                    
                    # AI-generated: Handle tender ban search tool calls
                    elif tool_name == "search_tender_bans":
                        logger.info(f"⏳ {tool_name} çalıştırılıyor...")
                        start_time = time.time()
                        try:
                            tool_output = search_tender_bans.invoke(tool_args)
                            elapsed_time = time.time() - start_time
                            logger.info(f"✅ {tool_name} tamamlandı ({elapsed_time:.2f} saniye)")
                        except Exception as tool_error:
                            elapsed_time = time.time() - start_time
                            logger.error(f"❌ {tool_name} BAŞARISIZ! ({elapsed_time:.2f} saniye)")
                            logger.error(f"   Hata: {tool_error}")
                            # Keep going with the other sources instead of failing the whole report
                            tool_error_msg = str(tool_error)
                            tool_output = []
                        
                        tender_ban_raw_data = tool_output if isinstance(tool_output, list) else []
                        logger.info(f"🚫 {len(tender_ban_raw_data)} adet ihale yasağı kaydı bulundu")
                        tool_output = self._format_tender_bans_for_llm(tender_ban_raw_data)
                        
                        # Log output size
                        output_json = json.dumps(tool_output, default=str, ensure_ascii=False)
                        logger.info(f"📊 Tool çıktı boyutu: {len(output_json)} karakter")
                    
                    else:
                        tool_output = f"Error: Unknown tool {tool_name}"
                        logger.error(f"❌ Bilinmeyen tool çağrısı: {tool_name}")
                    
                    if tool_error_msg:
                        tool_output = (
                            f"HATA: {tool_name} kaynağı sorgulanamadı ({tool_error_msg[:300]}). "
                            "Bu kaynak için veri yok. Raporda 'kayıt bulunmadı' değil, "
                            "'kaynak sorgulanamadı' olarak belirt."
                        )

                    # Add tool message
                    tool_message_content = json.dumps(tool_output, default=str)
                    logger.info(f"📨 ToolMessage ekleniyor (ID: {tool_call['id']}, Boyut: {len(tool_message_content)} karakter)")
                    messages.append(ToolMessage(content=tool_message_content, tool_call_id=tool_call["id"]))
                
                # DEBUG: Log message sizes before final LLM call
                logger.info("-" * 40)
                logger.info("📊 FİNAL LLM ÇAĞRISI ÖNCESİ - MESAJ BİLGİLERİ:")
                total_chars = sum(len(str(m.content)) if hasattr(m, 'content') else 0 for m in messages)
                logger.info(f"   Toplam mesaj sayısı: {len(messages)}")
                logger.info(f"   Toplam karakter sayısı: {total_chars}")
                
                # Approximate token count (rough estimate: 1 token ≈ 4 chars for Turkish)
                approx_tokens = total_chars // 3
                logger.info(f"   Tahmini token sayısı: ~{approx_tokens}")
                
                # Log each message size
                for i, msg in enumerate(messages):
                    msg_type = type(msg).__name__
                    msg_len = len(str(msg.content)) if hasattr(msg, 'content') else 0
                    logger.info(f"   [{i}] {msg_type}: {msg_len} karakter")
                
                if total_chars > 100000:
                    logger.warning(f"⚠️ UYARI: Toplam mesaj boyutu çok büyük! ({total_chars} karakter)")
                
                logger.info("-" * 40)
                logger.info("🔄 Final LLM çağrısı başlıyor (rapor oluşturma)...")
                llm_start_time = time.time()
                
                try:
                    final_response = await self.llm_with_tools.ainvoke(messages)
                    llm_elapsed = time.time() - llm_start_time
                    logger.info(f"✅ Final LLM çağrısı tamamlandı ({llm_elapsed:.2f} saniye)")
                    logger.info(f"📄 Rapor içeriği uzunluğu: {len(final_response.content) if final_response.content else 0} karakter")
                except Exception as llm_error:
                    llm_elapsed = time.time() - llm_start_time
                    logger.error(f"❌ FİNAL LLM ÇAĞRISI BAŞARISIZ! ({llm_elapsed:.2f} saniye)")
                    logger.error(f"   Hata tipi: {type(llm_error).__name__}")
                    logger.error(f"   Hata mesajı: {str(llm_error)}")
                    if hasattr(llm_error, 'response'):
                        logger.error(f"   Response status: {getattr(llm_error.response, 'status_code', 'N/A')}")
                    if hasattr(llm_error, '__cause__') and llm_error.__cause__:
                        logger.error(f"   Root cause: {llm_error.__cause__}")
                    raise
                
                report_content = final_response.content
            else:
                logger.warning("⚠️ LLM hiç tool çağrısı yapmadı, rapor oluşturulamıyor.")
                report_content = "Rapor oluşturulamadı: Agent gerekli aramaları başlatmadı."
            
            # Save to DB
            logger.info("-" * 40)
            logger.info("💾 VERİTABANI KAYIT İŞLEMLERİ")
            logger.info("-" * 40)
            
            logger.info(f"📰 Haber kayıtları kaydediliyor... (Toplam: {len(news_raw_data)})")
            news_count = self._save_news_records(news_raw_data, report.id)
            logger.info(f"✅ {news_count} haber kaydedildi")
            
            logger.info(f"📋 Sicil kayıtları kaydediliyor... (Toplam: {len(sicil_raw_data)})")
            sicil_count = self._save_sicil_records(sicil_raw_data, report.id)
            logger.info(f"✅ {sicil_count} sicil kaydı kaydedildi")
            
            # Update report
            report.content = report_content
            report.final_summary = report_content[:500] if report_content else None
            report.status = "COMPLETED"
            self.db.commit()
            
            logger.info("=" * 60)
            logger.info("🎉 RAPOR OLUŞTURMA TAMAMLANDI!")
            logger.info(f"   Rapor ID: {report.id}")
            logger.info(f"   Şirket: {company_name}")
            logger.info(f"   Haberler: {news_count}")
            logger.info(f"   Sicil Kayıtları: {sicil_count}")
            logger.info(f"   Rapor Uzunluğu: {len(report_content) if report_content else 0} karakter")
            logger.info("=" * 60)
            
            return {
                "report_id": report.id,
                "report_content": report_content,
                "news_count": news_count,
                "sicil_count": sicil_count
            }
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error("💥 RAPOR OLUŞTURMA BAŞARISIZ!")
            logger.error(f"   Hata Tipi: {type(e).__name__}")
            logger.error(f"   Hata Mesajı: {str(e)}")
            logger.error("=" * 60)
            
            self.db.rollback()
            report.status = "FAILED"
            report.content = f"Hata oluştu: {str(e)}"
            self.db.commit()
            raise e
