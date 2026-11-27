from playwright.sync_api import Page
import app.agents.sicil_gazetesi.scraper_engine.config as config
import app.agents.sicil_gazetesi.scraper_engine.utils as utils
import app.agents.sicil_gazetesi.scraper_engine.download_manager as download_manager
import time
import os
from app.logger import logger

# --- 1. FONKSİYON (jQuery Mask Sorunu Giderildi) ---
def fill_and_submit_announcement_form(page: Page, tsm_city, company_name, start_date=None, end_date=None):
    logger.info("--- İlan Görüntüleme Formu Dolduruluyor ---")
    
    try:
        page.goto(config.VIEW_URL)
        page.wait_for_load_state("domcontentloaded")
        
        # Formu Doldur
        page.select_option("#SicilMudurluguId", label=tsm_city)
        logger.info(f"Sicil Müd: {tsm_city} seçildi.")
        
        page.fill("#TicaretUnvani", company_name)
        
        # --- TARİH FİLTRESİ MANTIĞI ---
        if start_date and end_date:
            logger.info(f"📅 Tarih aralığı uygulanıyor: {start_date} - {end_date}")
            
            # Checkbox'ı işaretle
            page.check("#Tarih") 
            page.wait_for_selector("#DivTarih", state="visible")
            
            # Formatı düzelt (Sitede maske olduğu için sadece rakamları bile göndersek maske araya nokta koyabilir,
            # ama biz garanti olsun diye formatlı gönderip yavaş yazacağız)
            formatted_start = start_date.replace("/", ".")
            formatted_end = end_date.replace("/", ".")
            
            # --- BAŞLANGIÇ TARİHİ ---
            page.click("#Tarih1") 
            # DİKKAT: fill yerine type kullanıyoruz ve delay ekliyoruz
            # jQuery Mask'in algılaması için 100ms gecikmeli yazıyoruz.
            page.type("#Tarih1", formatted_start, delay=100)
            page.keyboard.press("Tab") 
            
            time.sleep(0.5) 
            
            # --- BİTİŞ TARİHİ ---
            page.click("#Tarih2")
            page.type("#Tarih2", formatted_end, delay=100)
            page.keyboard.press("Tab") 
            
            # Takvimi kapatmak için boşluğa tıkla
            page.locator("body").click()
            time.sleep(1) 
            
            logger.info("   -> Tarih alanları (insan simülasyonu ile) dolduruldu.")
        # ------------------------------

        # Butona tıkla
        search_btn = page.locator("button[type='submit'][data-message*='İlan Ara']")
        search_btn.scroll_into_view_if_needed()
        search_btn.click(force=True)
        
        logger.info("Sorgu gönderildi, sonuç bekleniyor...")
        time.sleep(2)
        
        # --- CAPTCHA KONTROLÜ ---
        if page.locator("#FormGuvenlikKodu").is_visible():
            logger.info("⚠️ Araya 'Güvenlik Kodu Doğrulama' sayfası girdi. Çözülüyor...")
            
            form_captcha = page.locator("#FormGuvenlikKodu")
            captcha_img = form_captcha.locator("#CaptchaImg")
            captcha_input = form_captcha.locator("#CaptchaIlan") 
            submit_btn = form_captcha.locator("button[type='submit']")
            
            code = utils.solve_captcha_element(captcha_img)
            logger.info(f"Ara Captcha Okundu: {code}")
            
            captcha_input.fill(code)
            submit_btn.click()
            logger.info("Doğrulama gönderildi.")
            time.sleep(2)
        
        try:
            # Tablonun gelmesini bekle
            page.wait_for_selector("#tblIlanGoruntuleme", state="visible", timeout=15000)
            logger.info(">>> Tablo görüntülendi. İndirme işlemine geçiliyor...")
            
            pdf_paths_list = process_and_extract_gazettes(page, company_name)
            return pdf_paths_list

        except Exception as e:
            content = page.content().lower()
            if "kayıt bulunamadı" in content:
                logger.info("Sonuç: Kayıt bulunamadı uyarısı tespit edildi (Veri gerçekten yok veya tarih maskesi yine hata verdi).")
            else:
                logger.error(f"❌ Tablo gelmedi. Hata detayı: {e}")
            return []

    except Exception as e:

        logger.error(f"İşlem Hatası: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        return []
# --- 2. FONKSİYON (Değişiklik burada) ---
def process_and_extract_gazettes(page: Page, company_name: str):
    links = page.locator("a:has(img[src*='icon_pdf.png'])")
    count = links.count()
    
    if count == 0: return [] # None yerine boş liste

    logger.info(f"--- '{company_name}' için {count} adet ilan bulundu ---")
    downloaded_paths = []

    for i in range(count):
        new_page = None
        try:
            logger.info(f"\n>> {i + 1}. İlan açılıyor...")

            with page.context.expect_page() as new_page_info:
                links.nth(i).click()
            
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            
            target_pdf_url = None
            current_url = new_page.url
            logger.info(f"   ℹ️  Sekme URL'i: {current_url}")

            if ".pdf" in current_url:
                target_pdf_url = current_url
            else:
                try:
                    embed_element = new_page.locator("embed[type='application/pdf']")
                    if embed_element.count() > 0:
                        target_pdf_url = embed_element.first.get_attribute("src")
                    else:
                        iframe_element = new_page.locator("iframe[src*='.pdf']")
                        if iframe_element.count() > 0:
                            target_pdf_url = iframe_element.first.get_attribute("src")
                except Exception as e:
                    logger.warning(f"   ⚠️ DOM taraması başarısız: {e}")

            if target_pdf_url:
                if not target_pdf_url.startswith("http"):
                     if target_pdf_url.startswith("/"):
                         base = "https://www.ticaretsicil.gov.tr"
                         target_pdf_url = base + target_pdf_url

                logger.info(f"   ⬇️  İndirme Başlatılıyor: {target_pdf_url}")
                
                api_response = page.context.request.get(target_pdf_url)
                
                if api_response.status == 200:
                    pdf_data = api_response.body()
                    
                    clean_name = company_name.replace(" ", "_").replace("/", "-").replace(".", "")
                    filename = f"{clean_name}_{i+1}.pdf"
                    
                    if not os.path.exists(config.DOWNLOAD_DIR):
                        os.makedirs(config.DOWNLOAD_DIR)
                        
                    save_path = os.path.join(config.DOWNLOAD_DIR, filename)

                    with open(save_path, "wb") as f:
                        f.write(pdf_data)
                    
                    logger.info(f"   ✅ BAŞARIYLA İNDİ: {filename}")
                    downloaded_paths.append(save_path)
                else:
                    logger.error(f"   ❌ İndirme Hatası. Status: {api_response.status}")
            else:
                logger.warning("   ⚠️ PDF URL'i bulunamadı.")

        except Exception as e:
            logger.error(f"   ❌ İşlem hatası: {e}")
        
        finally:
            if new_page:
                new_page.close()

    # BURASI KRİTİK: Artık listenin tamamını döndürüyoruz
    return downloaded_paths