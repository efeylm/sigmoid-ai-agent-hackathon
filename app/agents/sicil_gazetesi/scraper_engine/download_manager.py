from playwright.sync_api import Page
import os
import time
import app.agents.sicil_gazetesi.scraper_engine.config as config
from app.logger import logger

def process_and_extract_gazettes(page: Page, company_name: str):
    links = page.locator("a:has(img[src*='icon_pdf.png'])")
    count = links.count()
    
    if count == 0: return None

    logger.info(f"--- '{company_name}' için {count} adet ilan bulundu ---")
    downloaded_paths = []

    for i in range(count):
        new_page = None
        try:
            logger.info(f"\n>> {i + 1}. İlan açılıyor...")

            # 1. ADIM: Linke tıkla, yeni sekmeyi yakala
            with page.context.expect_page() as new_page_info:
                links.nth(i).click()
            
            new_page = new_page_info.value
            
            # Sayfa yüklenene kadar bekle
            new_page.wait_for_load_state("domcontentloaded")
            
            # Biraz bekle ki URL otursun (Redirect varsa)
            time.sleep(2)
            
            target_pdf_url = None
            current_url = new_page.url
            logger.info(f"   ℹ️  Sekme URL'i: {current_url}")

            # 2. ADIM: URL KONTROLÜ (Network Dinleme YOK)
            
            # SENARYO A: URL zaten .pdf ile bitiyor (Localde olan bu)
            if ".pdf" in current_url:
                logger.info("   🎯 URL direkt PDF formatında yakalandı.")
                target_pdf_url = current_url
            
            # SENARYO B: URL bir Viewer sayfası (.php vs) ama içinde PDF gömülü
            else:
                logger.info("   🔍 URL PDF değil, sayfa kaynağında (DOM) PDF aranıyor...")
                
                try:
                    # <embed src="..."> veya <iframe src="..."> etiketine bak
                    # Genelde Chrome PDF Viewer <embed> kullanır
                    embed_element = new_page.locator("embed[type='application/pdf']")
                    if embed_element.count() > 0:
                        target_pdf_url = embed_element.first.get_attribute("src")
                        logger.info(f"   🎯 DOM içinden PDF kaynağı bulundu: {target_pdf_url}")
                    else:
                        # Belki iframe vardır?
                        iframe_element = new_page.locator("iframe[src*='.pdf']")
                        if iframe_element.count() > 0:
                            target_pdf_url = iframe_element.first.get_attribute("src")
                            logger.info(f"   🎯 Iframe içinden PDF kaynağı bulundu: {target_pdf_url}")

                except Exception as e:
                    logger.error(f"   ⚠️ DOM taraması başarısız: {e}")

            # 3. ADIM: BULUNAN URL'İ İNDİR (Context API ile)
            if target_pdf_url:
                # URL bazen relative (göreli) olabilir, tam URL'e çevir
                if not target_pdf_url.startswith("http"):
                     # Base URL'i alıp birleştiriyoruz (Basit mantık)
                     # Ticaret sicil genelde absolute path verir ama garanti olsun
                     if target_pdf_url.startswith("/"):
                         base = "https://www.ticaretsicil.gov.tr"
                         target_pdf_url = base + target_pdf_url

                logger.info(f"   ⬇️  İndirme Başlatılıyor: {target_pdf_url}")
                
                # İndirme isteği
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
                    
                    logger.info(f"   ✅ BAŞARIYLA İNDİ: {filename} ({len(pdf_data)/1024:.1f} KB)")
                    downloaded_paths.append(save_path)
                else:
                    logger.error(f"   ❌ İndirme Hatası. Status: {api_response.status}")
            else:
                logger.warning("   ⚠️ PDF URL'i ne Adres Çubuğunda ne de DOM içinde bulunamadı.")
                # Son çare: HTML içeriğini basıp ne döndüğüne bakabilirsin (Debug için)
                # print(new_page.content())

        except Exception as e:
            logger.error(f"   ❌ İşlem hatası: {e}")
        
        finally:
            if new_page:
                new_page.close()

    if downloaded_paths:
        return downloaded_paths[0] 

    return None