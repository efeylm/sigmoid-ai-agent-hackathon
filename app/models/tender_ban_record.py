from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class TenderBanRecord(Base):
    __tablename__ = "tender_ban_records"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    
    # --- 1. ANA TANIMLAYICILAR ---
    banned_record_no = Column(String, index=True)   # YASAKLI KAYIT NO (Sağ Üst Köşe)
    tender_reg_no = Column(String, index=True)      # İhale Kayıt Numarası (İKN)
    decision_ministry = Column(String)              # Yasaklama Kararı Veren Kurum
    
    # --- 2. İDARE (KURUM) BİLGİLERİ ---
    authority_name = Column(String)                 # Adı (İdare)
    authority_address = Column(Text)                # Adresi (İdare)
    authority_postal_code = Column(String)          # Posta Kodu (İdare)
    authority_city = Column(String)                 # İl (İdare)
    authority_district = Column(String)             # İlçe (İdare)
    authority_phone_kep = Column(String)            # Tel-Kep (İdare)
    authority_email = Column(String)                # E-Posta (İdare)
    
    # --- 3. YASAKLI GERÇEK/TÜZEL KİŞİ BİLGİLERİ ---
    entity_type = Column(String)                    # Gerçek/Tüzel Kişi
    banned_name = Column(String, index=True)        # Adı/Unvanı
    banned_tc = Column(String, index=True)          # TC Kimlik No
    banned_tax_id = Column(String, index=True)      # Vergi Kimlik No
    banned_passport_no = Column(String)             # Pasaport No
    banned_address = Column(Text)                   # Adresi (Yasaklı)
    
    # --- 4. ORTAK (PARTNER) BİLGİLERİ ---
    partner_name = Column(String, nullable=True)    # Adı/Unvanı (Ortak)
    partner_city = Column(String, nullable=True)    # İl (Ortak)
    partner_district = Column(String, nullable=True)# İlçe (Ortak)
    partner_postal_code = Column(String, nullable=True)
    partner_address = Column(Text, nullable=True)   # Adres (Ortak)
    partnership_info = Column(Text, nullable=True)  # Ortaklık Bilgileri
    
    # --- 5. YASAKLAMA DETAYLARI ---
    legal_basis = Column(String)                    # Kanun Dayanağı
    ban_scope = Column(String)                      # Kapsam
    ban_duration = Column(String)                   # Süre
    ban_reason = Column(String)                     # Gerekçe
    
    # --- Metadata ---
    gazette_date = Column(String)                   # Resmi Gazete Tarihi
    gazette_no = Column(String)                     # Resmi Gazete Sayısı
    content = Column(Text)                          # OCR Ham Metin

    # İlişki
    report = relationship("Report", back_populates="ban_records")