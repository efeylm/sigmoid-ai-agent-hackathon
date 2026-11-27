# app/agents/news/service.py

from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool

from .schemas import NewsSearchRequest, NewsResponse, NewsItem
from .scrapers.tavily_client import TavilyScraper
from .scrapers.google_client import GoogleScraper
from .adapters import adapt_tavily_results, adapt_google_results
from app.models.news_record import NewsRecord
from app.models.company import Company
from app.models.report import Report

class NewsAgentService:
    def __init__(self, db: Session):
        self.db = db

    async def search_and_save(self, request: NewsSearchRequest) -> NewsResponse:
        """
        Scraper'ı çalıştırır, veriyi standartlaştırır, DB'ye yazar ve döner.
        """
        # 0. Şirket ve Rapor Hazırlığı
        company = self.db.query(Company).filter(Company.name == request.company_name).first()
        if not company:
            company = Company(name=request.company_name)
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)

        # Haberler için yeni bir rapor oluşturuyoruz
        report = Report(
            company_id=company.id,
            status="PROCESSING",
            content=f"{request.provider} üzerinden haber taraması başlatıldı."
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        results = []
        
        try:
            # 1. Scraper Seçimi ve Çalıştırma
            # Playwright blocking bir işlem olduğu için threadpool'da çalıştırıyoruz (FastAPI best practice)
            if request.provider.upper() == "TAVILY":
                scraper = TavilyScraper()
                # Tavily genelde hızlıdır ama yine de thread'e alabiliriz
                raw_data = await run_in_threadpool(
                    scraper.search, request.company_name, request.start_date, request.end_date
                )
                results = adapt_tavily_results(raw_data, request.company_name)
                
            elif request.provider.upper() == "GOOGLE":
                scraper = GoogleScraper()
                raw_data = await run_in_threadpool(
                    scraper.search, request.company_name, request.start_date, request.end_date
                )
                results = adapt_google_results(raw_data, request.company_name)

            # 2. Veritabanına Kayıt (Upsert Logic - URL varsa atla)
            saved_count = 0
            for item in results:
                if self._save_to_db(item, report.id):
                    saved_count += 1
            
            # Raporu güncelle
            report.status = "COMPLETED"
            report.content = f"{saved_count} haber bulundu ve kaydedildi."
            self.db.commit()

            # 3. Yanıt Oluşturma
            return NewsResponse(
                company=request.company_name,
                total_results=len(results),
                results=results
            )
            
        except Exception as e:
            report.status = "FAILED"
            report.content = f"Hata oluştu: {str(e)}"
            self.db.commit()
            raise e

    def _save_to_db(self, item: NewsItem, report_id: int) -> bool:
        # URL kontrolü (Mükerrer kayıt engelleme - Rapor bazlı değil genel kontrol yapılabilir, 
        # ama burada basitlik adına varsa eklemiyoruz diyelim veya rapora ekliyoruz)
        
        # Aynı URL bu rapor için var mı?
        exists = self.db.query(NewsRecord).filter(
            NewsRecord.report_id == report_id,
            NewsRecord.source_url == item.url
        ).first()
        
        if not exists:
            record = NewsRecord(
                report_id=report_id,
                headline=item.title,
                source_url=item.url,
                content=item.content,
                sentiment=item.sentiment,
                image_path=item.image_path,
                publication_date=item.published_date
                # source_provider alanı modelde yok, o yüzden eklemiyoruz.
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return True
        return False