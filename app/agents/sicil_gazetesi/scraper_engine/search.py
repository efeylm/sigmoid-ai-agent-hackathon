# search.py
from playwright.sync_api import Page
import app.agents.sicil_gazetesi.scraper_engine.config as config
import app.agents.sicil_gazetesi.scraper_engine.utils as utils
import time
from app.logger import logger

def search_company_title(page: Page, company_name):
    logger.info(f"--- '{company_name}' için Unvan Sorgulama Başlıyor ---")
    
    page.goto(config.SEARCH_URL)
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            logger.info(f"Sorgu Denemesi: {attempt + 1}")
            
            # --- DÜZELTME BURADA ---
            # Sayfadaki diğer gizli formlarla karışmaması için kapsamı (scope) daraltıyoruz.
            # Sadece id="FormUnvanSorgulama" olan formun içine bakacağız.
            form = page.locator("#FormUnvanSorgulama")
            
            # Formun görünür olmasını bekle
            form.wait_for(state="visible")
            
            # Artık tüm aramaları 'form' değişkeni üzerinden yapıyoruz.
            # Böylece sayfadaki diğer #CaptchaImg'leri görmezden gelir.
            unvan_input = form.locator("#UnvanSorgu")
            captcha_input = form.locator("#Captcha")
            captcha_img = form.locator("#CaptchaImg") # Artık hata vermez, formun içindekini alır
            
            # Butonu bul (Formun içindeki submit butonu)
            submit_btn = form.locator("button[type='submit']", has_text="SORGULA")
            
            # Captcha Çöz
            captcha_code = utils.solve_captcha_element(captcha_img)
            logger.info(f"Sorgu Captcha Okundu: {captcha_code}")
            
            # Doldur
            unvan_input.fill(company_name)
            captcha_input.fill(captcha_code)
            
            # Gönder
            submit_btn.click()
            
            # --- SONUÇLARI BEKLE ---
            try:
                # Sonuç tablosu: #DivUnvanSorgulamaSonuc içindeki tablo
                # (Sadece tablo görünür olana kadar bekle diyoruz)
                result_div = page.locator("#DivUnvanSorgulamaSonuc")
                result_div.wait_for(state="visible", timeout=5000)
                
                # Tablo satırlarını kontrol et
                table = result_div.locator("table")
                
                # Eğer tablo geldi ama içinde satır yoksa veya "Kayıt Bulunamadı" yazıyorsa
                if "kayıt bulunamadı" in result_div.inner_text().lower():
                    logger.info("Sorgu başarılı ama kayıt yok.")
                    return "KAYIT_YOK"

                logger.info(">>> SONUÇ TABLOSU GELDİ! <<<")
                
                # Tablonun ilk veri satırını al (Başlık hariç tbody)
                # Selenium kodunda: tr:first-child td:nth-child(4)
                first_row = table.locator("tbody tr").first
                tsm_value = first_row.locator("td").nth(3).inner_text().strip()
                
                tsm_value = first_row.locator("td").nth(3).inner_text().strip()
                
                logger.info(f"Tespit Edilen TSM (Şehir): {tsm_value}")
                return tsm_value

            except:
                # Tablo 5 saniye içinde gelmediyse hata mesajına bak
                # Sayfanın text içeriğini kontrol et
                content = page.locator("body").inner_text().lower()
                
                if "hatalı güvenlik kodu" in content:
                    logger.warning("Captcha yanlış girildi, sayfa yenileniyor...")
                    page.reload()
                elif "kayıt bulunamadı" in content:
                    return "KAYIT_YOK"
                else:
                    logger.warning("Tablo gelmedi ve hata mesajı tespit edilemedi. Tekrar deneniyor.")
                    page.reload()

        except Exception as e:
            logger.error(f"Sorgu hatası: {e}")
            page.reload()
            
    return None