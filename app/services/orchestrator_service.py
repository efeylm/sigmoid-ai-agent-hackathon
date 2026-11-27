import uuid
import json
import traceback
from sqlalchemy.orm import Session
from app.agents.orchestrator import master_app
from app.models.company import Company
from app.models.report import Report
from app.models.trade_registry_record import TradeRegistryRecord
from datetime import datetime
from app.logger import logger

async def run_full_process(db: Session, company_name: str, start_date: str = None, end_date: str = None):
    """
    AI Analizini başlatır ve sonuçları trade_registry_records tablosuna yazar.
    """
    
    # 1. Şirket Kontrolü
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        logger.info(f"🆕 Yeni şirket oluşturuluyor: {company_name}")
        company = Company(name=company_name)
        db.add(company)
        db.commit()
        db.refresh(company)

    # 2. Rapor Kaydı Oluştur
    process_id = str(uuid.uuid4())
    logger.info(f"🚀 Process Başladı: {process_id} | {company_name}")

    new_report = Report(
        company_id=company.id,
        status="PROCESSING",
        content="Analiz işlemleri devam ediyor..."
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # 3. AI Agent'ı Tetikle
    initial_state = {
        "company_name": company_name,
        "request_id": process_id,
        "start_date": start_date,
        "end_date": end_date,
        "errors": []
    }

    try:
        # LangGraph invoke (Asenkron)
        logger.info("🤖 AI Agent çalışıyor...")
        final_state = await master_app.ainvoke(initial_state)
        logger.info("✅ AI Agent tamamlandı.")
        
        # 4. Sicil Verilerini DB'ye Kaydet
        sicil_data = final_state.get("sicil_data", [])
        
        # --- DEBUG LOGLARI (SORUNU ÇÖZECEK KISIM) ---
        logger.debug(f"🔍 DEBUG: 'sicil_data' tipi: {type(sicil_data)}")
        logger.debug(f"🔍 DEBUG: 'sicil_data' uzunluğu: {len(sicil_data)}")
        if len(sicil_data) > 0:
            logger.debug(f"🔍 DEBUG: İlk öğenin anahtarları: {sicil_data[0].keys()}")
        # ----------------------------------------------

        if sicil_data:
            logger.info(f"💾 DB'ye {len(sicil_data)} adet sicil kaydı basılıyor...")
            
            for index, item in enumerate(sicil_data):
                try:
                    # 1. Details Verisini Güvenli Çek
                    # Agent bazen 'details', bazen 'details_json' dönebilir. İkisini de dene.
                    raw_details = item.get("details_json") or item.get("details") or {}
                    
                    # Eğer string geldiyse JSON'a çevir (Postgres JSONB bekler)
                    if isinstance(raw_details, str):
                        try:
                            raw_details = json.loads(raw_details)
                        except:
                            raw_details = {"error": "JSON parse hatası", "raw": raw_details}

                    # 2. Tarihi Güvenli Çek
                    announcement_date = raw_details.get("İlan Tarihi") if isinstance(raw_details, dict) else None

                    record = TradeRegistryRecord(
                        report_id=new_report.id,
                        summary=item.get("summary"),
                        risk_score=item.get("risk_score", 0),
                        details=raw_details, # JSON kolonu
                        announcement_date=announcement_date
                    )
                    db.add(record)
                    logger.info(f"   Writing Record #{index+1}: {item.get('summary')[:30]}...")

                except Exception as inner_e:
                    logger.error(f"⚠️ Kayıt döngüsünde hata (Atlanıyor): {inner_e}")
                    traceback.print_exc()

            # Toplu kayıt
            db.commit()
            logger.info("💾 Tüm sicil kayıtları başarıyla commit edildi.")
        else:
            logger.warning("⚠️ UYARI: 'sicil_data' boş döndü! DB'ye kayıt yapılmadı.")
        
        # 5. Raporu Tamamla
        final_report_text = final_state.get("final_report", "Rapor oluşturulamadı.")
        
        new_report.content = final_report_text
        new_report.status = "COMPLETED"
        db.commit()

        return {
            "status": "success",
            "process_id": process_id,
            "report_id": new_report.id,
            "final_report": final_report_text,
            "data_count": len(sicil_data)
        }

    except Exception as e:
        db.rollback()
        logger.error(f"🔥 KRİTİK SERVİS HATASI: {str(e)}", exc_info=True)
        traceback.print_exc() # Hatanın tam yerini gösterir
        
        new_report.status = "FAILED"
        new_report.content = f"Sistem hatası: {str(e)}"
        db.commit()
        raise e