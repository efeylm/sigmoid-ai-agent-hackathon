# app/agents/news/scrapers/google_client.py

import time
import random
import os
import hashlib
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from openai import OpenAI
from app.llm import completion_kwargs
from app.config import settings
from app.logger import logger

class GoogleScraper:
    def __init__(self):
        # --- KONFİGÜRASYON ---
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model_name = settings.OPENAI_MODEL_NAME
        self.output_folder = "haber_gorselleri_google"

        # OpenAI Client Başlatma
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key) if self.api_key else None

        # Whitelist
        self.turkish_domains = [
            "hurriyet.com.tr", "sabah.com.tr", "milliyet.com.tr", "sozcu.com.tr",
            "haberturk.com", "ntv.com.tr", "cnnturk.com", "trtworld.com",
            "aa.com.tr", "dunya.com", "ekonomim.com", "bloomberght.com",
            "paraanaliz.com", "bigpara.hurriyet.com.tr", "mynet.com",
            "ensonhaber.com", "t24.com.tr", "birgun.net", "yenicaggazetesi.com.tr",
            "yenisafak.com"
        ]

        # Klasör kontrolü
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def _safe_truncate(self, text: str, max_len: int = 500) -> str:
        if not text:
            return ""

        if len(text) <= max_len:
            return text

        cut = text[:max_len]
        last_dot = cut.rfind(".")
        if last_dot > 200:
            return cut[:last_dot + 1]

        return cut + "..."

    def _extract_snippet(self, card) -> str:
        """
        Google News kartından snippet (özet) metnini güvenli şekilde alır.
        Yoksa boş string döner.
        """
        selectors = [
            ".GI74Re",
            ".DnJfK",
            ".ST9BBe",
            "div[role='heading'] + div",
            "span"
        ]

        for sel in selectors:
            try:
                el = card.locator(sel).first
                if el.count() > 0:
                    text = el.text_content()
                    if text and len(text.strip()) > 20:
                        return text.strip()
            except:
                continue

        return ""


    def _is_turkish_source(self, url: str) -> bool:
        """URL'nin Türk haber kaynağı olup olmadığını kontrol eder"""
        try:
            domain = urlparse(url).netloc.lower()
            return any(td in domain for td in self.turkish_domains) or domain.endswith(".tr") or domain.startswith("tr.")
        except:
            return False

    def _is_relevant_to_company(self, text: str, company_name: str) -> bool:
        """Haberin şirketle ilgili olup olmadığını kontrol eder."""
        text_lower = text.lower()
        company_lower = company_name.lower()
        
        # Tam ad kontrolü
        if company_lower in text_lower:
            return True
        
        # Kısaltma kontrolü (En az 2 harfli baş harfler)
        initials = ''.join([word[0] for word in company_name.split() if word])
        if len(initials) >= 2 and initials.lower() in text_lower:
            return True
            
        return False

    def _extract_date_from_card(self, card) -> str:
        """Haber kartından tarih bilgisini çıkarır"""
        try:
            date_el = card.locator(".OSrXXb, .WG9SLd, .LEwnzc").first
            if date_el.is_visible():
                return date_el.text_content().strip()
        except:
            pass
        return "Tarih Belirtilmemiş"

    def _analyze_sentiment(self, text: str) -> str:
        """LLM ile duygu analizi yapar (Güvenli Mod)."""
        if not self.client or not text or len(text) < 10:
            return "NÖTR"

            system_prompt = """Sen uzman bir Borsa ve Finansal Duygu Analistisin. Görevin, verilen haber metinlerini şirket hisseleri ve marka itibarı üzerindeki etkisine göre sınıflandırmaktır.
            Analiz yaparken şu katı kuralları uygula:

                1. KRİTERLER:
                - OLUMLU: Şirket kârını, büyümesini, yeni yatırımlarını veya stratejik ortaklıklarını duyuran haberler. (Örn: "Şirket %20 büyüdü", "Yeni fabrika açılıyor")
                - OLUMSUZ: Şirket itibarını zedeleyen, "kriz", "skandal", "grev", "kötü muamele", "dava", "hırsızlık", "büyük müşteri kaybı" veya "zorunlu küçülme" içeren haberler.
                - NÖTR: Hisse fiyatını veya itibarı doğrudan etkilemeyecek genel bilgilendirmeler.

                2. İŞTEN ÇIKARMA (LAYOFF) DURUMLARI İÇİN ÖZEL KURAL:
                - Eğer işten çıkarma "stratejik yeniden yapılanma" ve "verimlilik" odaklıysa ve dil nötr/profesyonelse -> OLUMLU veya NÖTR olabilir.
                - Ancak; haberde "kıyım", "skandal", "tepki", "sendikal kriz", "korku" gibi ifadeler geçiyorsa bu bir PR krizidir -> Kesinlikle OLUMSUZ olarak etiketle.

                3. ÇIKTI FORMATI:
                Önce haberi kendi içinde bir cümle ile analiz et (Reasoning), sonra kararı ver. Ancak çıktı olarak SADECE aşağıdaki JSON formatını ver:
                {
                    "label": "OLUMLU" | "OLUMSUZ" | "NÖTR"
                } 
            """
            user_prompt = (
                f"Aşağıdaki haberin duygusunu TEK KELİME ile belirt.\n"
                f"SADECE şu kelimelerden birini yaz: OLUMLU, OLUMSUZ, NÖTR\n\n"
                f"Haber: {text[:800]}\n\n"
                f"Cevap (sadece tek kelime):"
            )

            

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **completion_kwargs(max_completion_tokens=300, temperature=0.1)
            )
            
            # NoneType hatasını önlemek için kontrol
            raw_content = response.choices[0].message.content
            if not raw_content:
                return "NÖTR"

            sentiment = raw_content.strip().upper()
            
            if "OLUMLU" in sentiment or "POZİTİF" in sentiment: return "OLUMLU"
            if "OLUMSUZ" in sentiment or "NEGATİF" in sentiment: return "OLUMSUZ"
            return "NÖTR"
            
        except Exception as e:
            logger.error(f"LLM Hatası: {e}")
            return "ANALIZ_HATASI"

    def search(self, company_name: str, start_date: str, end_date: str):
        """
        Google News üzerinde arama yapar.
        start_date/end_date formatı: MM/DD/YYYY (Google URL yapısı için)
        """
        # Google query string oluşturma
        # Not: Google URL'inde tarih MM/DD/YYYY formatında olmalı. 
        # Eğer input DD/MM/YYYY geliyorsa burada çevirmek gerekebilir. 
        # Şimdilik gelen formatı doğrudan kullanıyoruz.
        
        base_url = (
            f"https://www.google.com/search?q=\"{company_name}\"&tbm=nws&gl=tr&hl=tr&lr=lang_tr&"
            f"tbs=cdr:1,cd_min:{start_date},cd_max:{end_date},sbd:1"
        )
        
        all_results = []
        
        with sync_playwright() as p:
            # Headless=True yapıyoruz ki sunucuda UI açmaya çalışmasın
            browser = p.chromium.launch(
                headless=True, 
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--window-size=1920,1080"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="tr-TR",
                viewport={"width": 1920, "height": 1080},
                geolocation={"latitude": 41.0082, "longitude": 28.9784},
                permissions=["geolocation"]
            )
            
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = context.new_page()
            logger.info(f"🌍 Google News taranıyor: {company_name}")
            
            try:
                page.goto(base_url, timeout=60000)
            except:
                logger.warning("⚠️ Zaman aşımı, tekrar deneniyor...")
                try:
                    page.goto(base_url, timeout=60000)
                except:
                    browser.close()
                    return []

            time.sleep(random.uniform(2, 4))

            # Cookie Consent
            try:
                consent_btn = page.locator("button:has-text('Tümünü kabul et'), button:has-text('Kabul et')").first
                if consent_btn.is_visible(timeout=5000):
                    consent_btn.click()
                    time.sleep(1)
            except:
                pass

            page_number = 1
            max_pages = 5
            
            while page_number <= max_pages:
                # İçerik yüklenmesini bekle
                try:
                    page.wait_for_selector("div#search", timeout=15000)
                except:
                    logger.warning("⚠️ İçerik yüklenemedi (Captcha veya Sonuç Yok).")
                    break

                # Lazy load için scroll
                for _ in range(3):
                    page.mouse.wheel(0, 800)
                    time.sleep(0.5)

                cards = page.locator("div.SoaBEf, div[jsname='i05R6'], div.WlydOe")
                count = cards.count()

                if count == 0:
                    break

                logger.info(f"📄 Sayfa {page_number}: {count} haber bulundu.")

                for i in range(count):      
                    card = cards.nth(i)
                    try:
                        # Link
                        link_el = card.locator("a").first
                        if not link_el.is_visible(): continue
                        link = link_el.get_attribute("href")
                        
                        if not self._is_turkish_source(link): continue

                        # Başlık
                        title_el = card.locator("div[role='heading']").first
                        title = title_el.text_content() if title_el.is_visible() else ""

                        snippet_text = self._extract_snippet(card)
                        # Full text (LLM & relevance için)
                        if snippet_text:
                            full_text = f"{title}. {snippet_text}"
                        else:
                            full_text = title   
                        
                        # İlgililik Kontrolü
                        if not self._is_relevant_to_company(full_text, company_name):
                            continue

                        # Tarih
                        tarih = self._extract_date_from_card(card)

                        # LLM Analizi
                        kategori = self._analyze_sentiment(full_text)

                        # Görsel İşleme (Screenshot)
                        url_hash = hashlib.md5(link.encode('utf-8')).hexdigest()
                        image_path = os.path.join(self.output_folder, f"{url_hash}.jpg")
                        
                        thumbnail_el = card.locator(".uhHOwf img, img").first
                        final_image_path = None # DB'ye null gitsin diye None yapıyoruz, yoksa path döner

                        if thumbnail_el.is_visible():
                            if os.path.exists(image_path):
                                final_image_path = image_path
                            else:
                                try:
                                    thumbnail_el.scroll_into_view_if_needed()
                                    time.sleep(0.1)
                                    thumbnail_el.screenshot(path=image_path, type="jpeg", quality=80)
                                    final_image_path = image_path
                                except:
                                    pass

                        # Duplicate kontrolü ve Ekleme
                        if title and link:
                            if not any(r['web_linki'] == link for r in all_results):
                                all_results.append({
                                    "baslik": title,
                                    "web_linki": link,
                                    "text_metni": self._safe_truncate(full_text,),
                                    "kategorisi": kategori,
                                    "jpeg_goruntusu": final_image_path,
                                    "tarih": tarih
                                })
                    except Exception as e:
                        logger.error(f"Kart hatası: {e}")
                        continue
                
                # Sonraki Sayfa
                next_button = page.locator("a#pnnext").first
                if next_button.is_visible():
                    time.sleep(random.uniform(2, 4))
                    next_button.click()
                    page_number += 1
                else:
                    break
            
            browser.close()
            
        return all_results