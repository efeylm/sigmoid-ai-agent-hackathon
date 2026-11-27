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
            
            # OR koşulları ile dinamik query oluştur (SQLAlchemy text() ile güvenli)
            conditions = " OR ".join([f"banned_name ILIKE :pattern_{i}" for i in range(len(search_patterns))])

            # tender_ban_records has no machine-readable date column (gazette_date is free text),
            # so results are not filtered by date here.
            date_filter = ""
            
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
                    entity_type,
                    banned_name,
                    banned_tc,
                    banned_tax_id,
                    banned_passport_no,
                    banned_address,
                    legal_basis,
                    ban_scope,
                    ban_duration,
                    partner_name,
                    partnership_info,
                    ban_reason,
                    gazette_date,
                    gazette_no
                FROM public.tender_ban_records
                WHERE ({conditions})
                {date_filter}
                ORDER BY gazette_date DESC
                LIMIT 50
            """)
            
            # Parametreleri dict olarak hazırla
            params = {f"pattern_{i}": pattern for i, pattern in enumerate(search_patterns)}
            
            result = db.execute(query, params)
            rows = result.fetchall()
            logger.info(f"📊 DB'den {len(rows)} adet ihale yasağı kaydı çekildi")
            logger.info(f"🔍 Arama pattern'leri: {search_patterns}")
            
            records = []
            for row in rows:
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
                    "entity_type": row.entity_type,
                    "banned_name": row.banned_name,
                    "banned_tc": row.banned_tc,
                    "banned_tax_id": row.banned_tax_id,
                    "banned_address": row.banned_address,
                    "legal_basis": row.legal_basis,
                    "ban_scope": row.ban_scope,
                    "ban_duration": row.ban_duration,
                    "partner_name": row.partner_name,
                    "ban_reason": row.ban_reason,
                    "gazette_date": row.gazette_date,
                    "gazette_no": row.gazette_no,
                    "source_url": None
                })
            
            return records
        finally:
            db.close()