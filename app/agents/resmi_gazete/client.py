# app/agents/resmi_gazete/client.py
import json
from typing import List, Dict, Any
from sqlalchemy import text
from app.db import SessionLocal
from app.logger import logger


class TenderBanClient:
    """
    scraped_tender_bans tablosundan ihale yasaklılarını sorgular.
    """

    def _generate_search_patterns(self, company_name: str) -> List[str]:
        """
        Şirket adından arama varyasyonları üretir.
        Yasal son ekleri (Anonim Şirketi, Limited Şirketi vb.) çıkarır.
        Hem büyük hem küçük harfli versiyonlar üretir.
        """
        if not company_name:
            return []

        clean_name = company_name.strip()
        
        # Yasal son ekleri çıkar
        legal_suffixes = [
            "ANONİM ŞİRKETİ",
            "ANONIM SIRKETI", 
            "ANONİM ŞTİ",
            "ANONIM STI",
            "A.Ş.",
            "A.S.",
            "LİMİTED ŞİRKETİ",
            "LIMITED SIRKETI",
            "LİMİTED ŞTİ",
            "LIMITED STI",
            "LTD. ŞTİ.",
            "LTD. STI.",
            "LTD ŞTİ",
            "LTD STI"
        ]
        
        # Büyük harfli versiyondan son ekleri çıkar
        clean_name_upper = clean_name.upper()
        for suffix in legal_suffixes:
            if clean_name_upper.endswith(suffix):
                clean_name = clean_name[:len(clean_name) - len(suffix)].strip()
                break
        
        # Sondaki nokta ve virgülleri temizle
        clean_name = clean_name.rstrip('.,;')
        
        patterns = []
        
        # 1. Orijinal (yasal son ek çıkarılmış) - büyük harf
        patterns.append(f"%{clean_name.upper()}%")
        
        # 2. Orijinal (yasal son ek çıkarılmış) - küçük harf (title case)
        patterns.append(f"%{clean_name.title()}%")
        
        # 3. Orijinal (yasal son ek çıkarılmış) - tam küçük harf
        patterns.append(f"%{clean_name.lower()}%")
        
        return list(set(patterns))  # Tekrarları önle


    def _convert_date_format(self, date_str: str) -> str:
        """
        DD/MM/YYYY formatını YYYYMMDD formatına çevirir.
        Örn: "14/12/2024" -> "20241214"
        """
        if not date_str:
            return None
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = parts
                return f"{year}{month.zfill(2)}{day.zfill(2)}"
        except:
            pass
        return None

    def search(self, company_name: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """
        Şirket adına göre ihale yasaklılarını arar.
        
        Args:
            company_name: Aranacak şirket adı/ünvanı
            
        Returns:
            İhale yasaklı kayıtlarının listesi
        """
        db = SessionLocal()
        try:
            search_patterns = self._generate_search_patterns(company_name)
            
            if not search_patterns:
                return []

            # Tarih formatını dönüştür (DD/MM/YYYY -> YYYYMMDD)
            start_date_formatted = self._convert_date_format(start_date) if start_date else None
            end_date_formatted = self._convert_date_format(end_date) if end_date else None
            
            # OR koşulları ile dinamik query oluştur (SQLAlchemy text() ile güvenli)
            conditions = " OR ".join([f"banned_name ILIKE :pattern_{i}" for i in range(len(search_patterns))])

            date_filter = ""
            if start_date_formatted and end_date_formatted:
                date_filter = """
                    AND CAST((source_metadata->>'date') AS INTEGER) >= :start_date
                    AND CAST((source_metadata->>'date') AS INTEGER) <= :end_date
                """
            
            query = text(f"""
                SELECT 
                    id,
                    banned_record_no,
                    tender_reg_no,
                    decision_ministry,
                    authority_name,
                    authority_address,
                    authority_postal_code,
                    authority_city,
                    authority_district,
                    authority_phone_kep,
                    authority_email,
                    banned_entity_type,
                    banned_name,
                    banned_tc,
                    banned_tax_id,
                    banned_passport_no,
                    banned_address,
                    ban_details_legal_basis,
                    ban_details_scope,
                    ban_details_duration,
                    partner,
                    partnership_info,
                    source_metadata,
                    ban_reason,
                    gazette_date,
                    gazette_no,
                    created_at
                FROM public.tender_ban_records
                WHERE ({conditions})
                {date_filter}
                ORDER BY gazette_date DESC
                LIMIT 50
            """)
            
            # Parametreleri dict olarak hazırla
            params = {f"pattern_{i}": pattern for i, pattern in enumerate(search_patterns)}
            if start_date_formatted and end_date_formatted:
                params["start_date"] = start_date_formatted
                params["end_date"] = end_date_formatted
            
            result = db.execute(query, params)
            rows = result.fetchall()
            logger.info(f"📊 DB'den {len(rows)} adet ihale yasağı kaydı çekildi")
            logger.info(f"🔍 Arama pattern'leri: {search_patterns}")
            if start_date_formatted and end_date_formatted:
                logger.info(f"📅 Tarih filtresi: {start_date_formatted} - {end_date_formatted}")
            
            records = []
            for row in rows:
                # source_metadata JSON'dan URL çıkar
                source_url = None
                if row.source_metadata:
                    try:
                        metadata = json.loads(row.source_metadata) if isinstance(row.source_metadata, str) else row.source_metadata
                        source_url = metadata.get("source_url")
                    except:
                        pass
                
                records.append({
                    "id": row.id,
                    "banned_record_no": row.banned_record_no,
                    "tender_reg_no": row.tender_reg_no,
                    "decision_ministry": row.decision_ministry,
                    "authority_name": row.authority_name,
                    "authority_address": row.authority_address,
                    "authority_city": row.authority_city,
                    "authority_district": row.authority_district,
                    "authority_phone_kep": row.authority_phone_kep,
                    "entity_type": row.banned_entity_type,
                    "banned_name": row.banned_name,
                    "banned_tc": row.banned_tc,
                    "banned_tax_id": row.banned_tax_id,
                    "banned_address": row.banned_address,
                    "legal_basis": row.ban_details_legal_basis,
                    "ban_scope": row.ban_details_scope,
                    "ban_duration": row.ban_details_duration,
                    "ban_reason": row.ban_reason,
                    "gazette_date": row.gazette_date,
                    "gazette_no": row.gazette_no,
                    "source_url": source_url
                })
            
            return records
        finally:
            db.close()