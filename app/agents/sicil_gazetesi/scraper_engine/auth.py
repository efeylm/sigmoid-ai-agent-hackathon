# auth.py
from playwright.sync_api import Page
import app.agents.sicil_gazetesi.scraper_engine.config as config
import app.agents.sicil_gazetesi.scraper_engine.utils as utils
import time
from app.logger import logger

def login(page: Page):
    logger.info("--- Giriş İşlemi Başlatılıyor ---")
    
    for attempt in range(5):
        try:
            logger.info(f"Login Denemesi: {attempt + 1}")
            page.goto(config.LOGIN_URL)
            
            # "GİRİŞ" butonuna tıkla
            page.get_by_text("GİRİŞ", exact=False).first.click()
            
            # Giriş formunun (Modal) görünür olmasını bekle
            # #FormUyeGirisi id'li formun görünmesini bekliyoruz
            page.wait_for_selector("#FormUyeGirisi", state="visible")
            
            # --- DÜZELTİLEN KISIM ---
            # HTML'e göre doğru ID ve Name değerlerini girdim
            
            # Formun kendisine odaklanıyoruz
            form = page.locator("#FormUyeGirisi")
            
            # HTML'de id="LoginEmail" olarak geçiyor
            email_input = form.locator("#LoginEmail") 
            
            # HTML'de id="LoginSifre" olarak geçiyor
            pass_input = form.locator("#LoginSifre")
            
            # HTML'de id="Captcha" ve id="CaptchaImg"
            captcha_input = form.locator("#Captcha")
            captcha_img = form.locator("#CaptchaImg") 
            
            submit_btn = form.locator("button[type='submit']")

            # Captcha Çöz
            code = utils.solve_captcha_element(captcha_img)
            logger.info(f"Login Captcha Okundu: {code}")
            
            # Formu Doldur
            email_input.fill(config.USER_EMAIL)
            pass_input.fill(config.USER_PASS)
            captcha_input.fill(code)
            
            # Gönder
            submit_btn.click()
            
            # Giriş Başarılı Kontrolü
            try:
                # Giriş yapınca "ÇIKIŞ" yazısı gelmeli
                page.wait_for_selector("text=ÇIKIŞ", timeout=5000)
                logger.info(">>> Giriş Başarılı")
                return True
            except:
                # Hata mesajı var mı kontrol et
                if page.locator(".alert-danger").is_visible():
                    err_text = page.locator(".alert-danger").inner_text()
                    logger.error(f"Site Hatası: {err_text}")
                logger.warning("Giriş yapılamadı, tekrar deneniyor...")
                
        except Exception as e:
            logger.error(f"Login hatası: {e}")
            
    return False