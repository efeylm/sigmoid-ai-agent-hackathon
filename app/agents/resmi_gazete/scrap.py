import argparse
import requests
import json
import time
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from io import BytesIO
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import numpy as np
import cv2

from ai_parser import parse_text_with_ai
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from db_importer import flatten_record, get_db_engine, create_tables, ScrapedTenderBan
from sqlalchemy.orm import sessionmaker

class DateRangeScanner:
    BASE_URL = "https://www.resmigazete.gov.tr"
    # Kesin eşleşme için tam başlık
    EXACT_KEYWORD = "İHALELERE KATILMAKTAN YASAKLAMA KARARI"

    def __init__(self, start_date_str, end_date_str, use_db=True):
        self.start_date = datetime.strptime(start_date_str, "%Y%m%d")
        self.end_date = datetime.strptime(end_date_str, "%Y%m%d")
        self.use_db = use_db
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
        })

        # Veritabanı bağlantısı
        self.db_engine = None
        self.db_session = None
        
        if self.use_db:
            self.db_engine = get_db_engine()
            if self.db_engine:
                create_tables(self.db_engine)
                Session = sessionmaker(bind=self.db_engine)
                self.db_session = Session()
                print("✅ Veritabanı bağlantısı kuruldu.")
            else:
                print("❌ Veritabanı bağlantısı kurulamadı, kayıtlar atlanacak!")
                self.use_db = False

    def get_date_range(self):
        """İki tarih arasındaki tüm günleri (tarih stringi olarak) döndür."""
        current = self.start_date
        while current <= self.end_date:
            yield current.strftime("%Y%m%d")
            current += timedelta(days=1)

    def normalize_for_search(self, text):
        """Basit normalizasyon (Büyük harf + Türkçe karakter düzeltme)"""
        tr_map = {"Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U", "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}
        text = text.upper()
        for src, dst in tr_map.items():
            text = text.replace(src, dst)
        return text

    def get_pdf_urls_for_date(self, date_str):
        """Belirtilen tarihteki 4. Kısım ilanlarının PDF linklerini bul."""
        year = date_str[:4]
        month = date_str[4:6]
        url = f"{self.BASE_URL}/ilanlar/eskiilanlar/{year}/{month}/{date_str}-4.htm"
        
        try:
            r = self.session.get(url, timeout=30)
            if r.status_code == 404:
                return self.probe_pdf_urls(date_str)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  ❌ Sayfa erişim hatası ({date_str}): {e}")
            return []

        soup = BeautifulSoup(r.content, "html.parser")
        pdf_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            
            if re.search(rf"{date_str}-4-\d+\.pdf", href):
                if "/" not in href:
                    full_url = f"{self.BASE_URL}/ilanlar/eskiilanlar/{year}/{month}/{href}"
                else:
                    full_url = urljoin(self.BASE_URL, href)
                    
                pdf_urls.add(full_url)
        
        urls_list = sorted(list(pdf_urls))
        if not urls_list:
             return self.probe_pdf_urls(date_str)
             
        return urls_list

    def probe_pdf_urls(self, date_str, max_probe=10):
        year = date_str[:4]
        month = date_str[4:6]
        valid_urls = []
        
        print(f"  ⚠️ Fallback: {date_str} için PDF'ler taranıyor...")
        for i in range(1, max_probe + 1):
            url = f"{self.BASE_URL}/ilanlar/eskiilanlar/{year}/{month}/{date_str}-4-{i}.pdf"
            try:
                r = self.session.head(url, timeout=5)
                if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("application/pdf"):
                    valid_urls.append(url)
            except:
                pass
        return valid_urls

    def download_pdf(self, url):
        try:
            r = self.session.get(url, timeout=60, stream=True)
            r.raise_for_status()
            
            content_type = r.headers.get("Content-Type", "").lower()
            if "application/pdf" not in content_type:
                first_bytes = r.raw.read(4)
                if not first_bytes.startswith(b"%PDF"):
                    return None
                remaining = r.raw.read()
                return BytesIO(first_bytes + remaining)
            
            return BytesIO(r.content)
        except Exception as e:
            print(f"  ❌ İndirme hatası: {url} -> {e}")
            return None

    def preprocess_image(self, img_pil):
        """
        Görüntüdeki dikey ve yatay çizgileri (tabloyu) tamamen siler.
        Böylece Tesseract metin bloklarını satır olarak daha iyi algılar.
        """
        img = np.array(img_pil)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Binary threshold (Yazılar siyah, arka plan beyaz olacak şekilde ayarla)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        
        # 1. DİKEY ÇİZGİLERİ BUL
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, img.shape[0] // 50))
        vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        vertical_lines = cv2.dilate(vertical_lines, None, iterations=2)
        
        # 2. YATAY ÇİZGİLERİ BUL
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (img.shape[1] // 40, 1))
        horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        horizontal_lines = cv2.dilate(horizontal_lines, None, iterations=2)
        
        # 3. ÇİZGİLERİ BİRLEŞTİR (Tablo İskeleti)
        table_mask = cv2.add(vertical_lines, horizontal_lines)
        
        # 4. ORİJİNAL RESİMDEN SİL (Beyaza boya)
        img_no_lines = img.copy()
        img_no_lines[table_mask > 0] = (255, 255, 255)
        
        return img_no_lines

    def get_text_rows(self, img_no_lines):
        """
        Tablosuz resimdeki metin satırlarını tespit eder.
        """
        gray = cv2.cvtColor(img_no_lines, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        
        # Yatayda metinleri birleştir (Dilate)
        # Kernel: (Genişlik, Yükseklik) -> Genişliği artırarak kelimeleri satır haline getiriyoruz
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        
        # Konturları bul (Her biri bir satır olacak)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rows = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Çok küçük gürültüleri ele (Örn: tek nokta, leke)
            if w > 20 and h > 5:
                rows.append((y, y+h, x, x+w)) # y_top, y_bottom, x_left, x_right
        
        # Yukarıdan aşağıya sırala
        rows.sort(key=lambda r: r[0])
        return rows

    def extract_text_smart(self, pdf_bytes, pdf_url):
        """
        pypdf ile metin çıkarır, eğer başlık varsa o metni kullanır.
        Yoksa OCR ile tarar, satırları analiz eder ve debug resimleri oluşturur.
        """
        pdf_bytes.seek(0)
        
        # 1. Önce Hızlı Text (pypdf) - Keyword Kontrolü
        keyword_found_in_text = False
        try:
            reader = PdfReader(pdf_bytes)
            raw_text = ""
            for page in reader.pages:
                raw_text += (page.extract_text() or "") + "\n"
                
            # Filtreleme: "Yürütmeyi Durdurma" gibi ifadeleri ele
            norm_raw = self.normalize_for_search(raw_text)
            norm_key = self.normalize_for_search(self.EXACT_KEYWORD)
            
            # SADECE tam başlık varsa OCR'a geç
            if norm_key in norm_raw:
                # Yürütmenin durdurulması kontrolü (çeşitli varyasyonlar)
                durdurma_keywords = [
                    "YURUTMENIN DURDURULMASI",
                    "YURUTMESININ DURDURULMASI", 
                    "DURDURULMASINA",
                    "YURUTMENIN DURDURULMASINA",
                    "DURDURULMASI ILISKIN",
                    "YURUTME DURDURMA"
                ]
                
                for keyword in durdurma_keywords:
                    if keyword in norm_raw:
                        print("    ⚠️ 'Yürütmenin Durdurulması' kararı algılandı, atlanıyor.")
                        return None
                
                # Keyword bulundu, OCR taraması yapılacak
                print("    ✅ Metin tabanlı kontrolde keyword bulundu, OCR taraması başlatılıyor...")
                keyword_found_in_text = True
            else:
                # Keyword yok, OCR'a gerek yok
                print("    ℹ️ Metin tabanlı kontrolde keyword bulunamadı, OCR atlanıyor.")
                return None
        except Exception:
            # pypdf başarısız olursa OCR'a geç
            print("    ⚠️ pypdf başarısız oldu, OCR taramasına geçiliyor...")
            keyword_found_in_text = True

        # 2. OCR Taraması (Sadece keyword bulunmuşsa)
        if not keyword_found_in_text:
            return None
            
        pdf_bytes.seek(0)
        final_text = ""
        found_keyword = False
        POPPLER_YOLU = r"C:\Program Files\poppler-25.12.0\Library\bin"  # <-- BURAYI GÜNCELLEYİN
        try:
            images = convert_from_bytes(pdf_bytes.read(), dpi=300, poppler_path=POPPLER_YOLU)
            pdf_name = pdf_url.split("/")[-1]
            
            for i, img in enumerate(images):
                print(f"      -> Sayfa {i+1} inceleniyor... (Resim Boyutu: {img.size})")
                
                # Görüntüyü işle (Tabloyu tamamen sil)
                img_processed = self.preprocess_image(img)
                
                # Satırları tespit et
                rows = self.get_text_rows(img_processed)
                
                # Satır satır OCR yap ve birleştir
                page_text = ""
                
                for (y1, y2, x1, x2) in rows:
                    # Satırı biraz genişlet (padding)
                    pad = 2
                    y1 = max(0, y1 - pad)
                    y2 = min(img_processed.shape[0], y2 + pad)
                    
                    # Tüm genişliği kullan (Sağ taraftaki boşlukları da okumak için)
                    roi = img_processed[y1:y2, 0:img_processed.shape[1]]
                    
                    # Satırı OCR yap (psm 7 = tek satır)
                    line_text = pytesseract.image_to_string(roi, lang="tur", config="--psm 7").strip()
                    
                    if line_text:
                        page_text += line_text + "\n"
                
                norm_text = self.normalize_for_search(page_text)
                norm_key = self.normalize_for_search(self.EXACT_KEYWORD)
                
                if norm_key in norm_text:
                    # Yürütmenin durdurulması kontrolü (OCR seviyesinde)
                    durdurma_keywords = [
                        "YURUTMENIN DURDURULMASI",
                        "YURUTMESININ DURDURULMASI",
                        "DURDURULMASINA",
                        "YURUTMENIN DURDURULMASINA",
                        "DURDURULMASI ILISKIN",
                        "YURUTME DURDURMA"
                    ]
                    
                    for keyword in durdurma_keywords:
                        if keyword in norm_text:
                            print(f"      ⚠️ Sayfa {i+1}: 'Yürütmenin Durdurulması' kararı (OCR), atlanıyor.")
                            return None
                        
                    found_keyword = True
                    print(f"      ✅ Sayfa {i+1}: Yasaklama kararı bulundu.")
                    final_text += page_text + "\n"
                else:
                    # Bu sayfada karar yoksa bile metni ekle (devam sayfası olabilir)
                    final_text += page_text + "\n"
            
            if found_keyword:
                return final_text
                
        except Exception as e:
            print(f"    ❌ OCR Hatası: {e}")
            
        return None

    def process_date_range(self):
        print(f"🚀 Tarama Başlıyor: {self.start_date.strftime('%Y-%m-%d')} -> {self.end_date.strftime('%Y-%m-%d')}")
        
        for date_str in self.get_date_range():
            print(f"\n📅 İşleniyor: {date_str}")
            pdf_urls = self.get_pdf_urls_for_date(date_str)
            
            if not pdf_urls:
                print("  -> PDF bulunamadı.")
                continue
                
            print(f"  -> {len(pdf_urls)} adet PDF bulundu.")
            
            for url in pdf_urls:
                print(f"  🔍 İnceleniyor: {url}")
                pdf_bytes = self.download_pdf(url)
                if not pdf_bytes: continue
                
                # Akıllı OCR ve Filtreleme
                text = self.extract_text_smart(pdf_bytes, url)
                
                if text:
                    print(f"    ✅ Geçerli Yasaklama Kararı! -> AI ile işleniyor...")
                    
                    try:
                        # parse_text_with_ai artık bir LİSTE döndürüyor (tek kayıt olsa bile liste içinde)
                        parsed_data_list = parse_text_with_ai(text)
                        
                        if parsed_data_list:
                            for record in parsed_data_list:
                                # Her bir kayda metadata ekle
                                record["metadata"] = {
                                    "source_url": url,
                                    "date": date_str,
                                    "scan_timestamp": datetime.now().isoformat()
                                }
                                # Hemen veritabanına kaydet
                                self.save_to_db(record)
                            
                            print(f"    💾 {len(parsed_data_list)} adet veri veritabanına kaydedildi.")
                    except Exception as e:
                        print(f"    ❌ AI Parse Hatası: {e}")
                else:
                    # Yasaklama kararı içermiyor veya filtrelendi
                    pass
                    
    def save_to_db(self, record):
        """Tek bir kaydı veritabanına kaydet."""
        if not self.use_db or not self.db_session:
            return
        
        try:
            flat_record = flatten_record(record)
            db_record = ScrapedTenderBan(**flat_record)
            self.db_session.add(db_record)
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            print(f"    ❌ DB Kayıt Hatası: {e}")
    
    def close_db(self):
        """Veritabanı bağlantısını kapat."""
        if self.db_session:
            self.db_session.close()
            print("🔒 Veritabanı bağlantısı kapatıldı.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tarih aralığındaki yasaklama kararlarını tara ve veritabanına kaydet.")
    parser.add_argument("start_date", help="Başlangıç Tarihi (YYYYMMDD)")
    parser.add_argument("end_date", help="Bitiş Tarihi (YYYYMMDD)")
    parser.add_argument("--no-db", action="store_true", help="Veritabanına kaydetme (sadece tarama)")
    
    args = parser.parse_args()
    
    scanner = DateRangeScanner(args.start_date, args.end_date, use_db=not args.no_db)
    
    try:
        scanner.process_date_range()
    finally:
        scanner.close_db()
    
    print(f"\n🏁 İşlem Tamamlandı. Veriler veritabanına kaydedildi.")