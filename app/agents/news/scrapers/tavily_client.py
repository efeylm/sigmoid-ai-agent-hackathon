# app/agents/news/scrapers/tavily_client.py

import os
import requests
import hashlib
from bs4 import BeautifulSoup
from tavily import TavilyClient
from openai import OpenAI
from app.llm import completion_kwargs
from app.config import settings
import re
from app.logger import logger

class TavilyScraper:
    def __init__(self):
        # --- KONFİGÜRASYON ---
        self.tavily_api_key = settings.TAVILY_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self.model_name = settings.OPENAI_MODEL_NAME
        self.output_folder = "haber_gorselleri_tavily"

        # İstemcileri Başlat
        self.tavily_client = TavilyClient(api_key=self.tavily_api_key)
        self.llm_client = OpenAI(base_url=self.base_url, api_key=self.openai_api_key)

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

    def _is_relevant_to_company(self, text: str, company_name: str) -> bool:
        text_lower = text.lower()
        company_lower = company_name.lower()

        # Tam ad
        if company_lower in text_lower:
            return True

        # Kısaltma (örn: Türkiye İş Bankası → TİB)
        initials = ''.join([w[0] for w in company_name.split() if w])
        if len(initials) >= 2 and initials.lower() in text_lower:
            return True

        return False


    def _format_date_for_tavily(self, date_str: str) -> str:
        """DD/MM/YYYY formatını Tavily'nin istediği YYYY-MM-DD formatına çevirir."""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        except:
            pass
        return date_str

    def _download_image(self, image_url: str) -> str:
        """Verilen URL'deki görseli indirir."""
        if not image_url: return None
        
        try:
            # Dosya adı oluştur (URL hash)
            url_hash = hashlib.md5(image_url.encode('utf-8')).hexdigest()
            
            # Uzantı kontrolü
            ext = '.jpg'
            if '.' in image_url.split('?')[0]:
                parts = image_url.split('?')[0].split('.')
                if len(parts[-1]) <= 5: # jsp, php gibi uzun uzantıları engelle
                    ext = '.' + parts[-1]

            file_path = os.path.join(self.output_folder, f"{url_hash}{ext}")
            
            # Cache kontrolü
            if os.path.exists(file_path): 
                return file_path 
            
            # İndirme işlemi
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(image_url, stream=True, timeout=10, headers=headers)
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                return None

            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return file_path
        except Exception as e:
            logger.warning(f"  ⚠️ Görsel indirilemedi ({image_url[:30]}...): {e}")
            pass
        return None

    def _get_article_image(self, url: str) -> str:
        """
        Haber URL'sinden Open Graph veya Twitter Card görselini çeker.
        Bu yöntem Tavily'nin döndüğü thumbnail'den daha kalitelidir.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=8, headers=headers)
            
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Open Graph Image
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                img_url = og_image['content']
                if img_url.startswith('//'): img_url = 'https:' + img_url
                return img_url
            
            # 2. Twitter Card Image
            twitter_image = soup.find('meta', {'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                return twitter_image['content']
            
        except Exception:
            pass # Sessizce başarısız ol, akışı bozma
        return None

    def _analyze_sentiment(self, text: str) -> str:
        """LLM ile duygu analizi yapar (Güvenli Mod)."""
        if not self.llm_client or not text or len(text) < 10:
            return "NÖTR"
        
        try:
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

            

            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **completion_kwargs(max_completion_tokens=300, temperature=0.1)
            )
            
            raw_content = response.choices[0].message.content
            if not raw_content: return "NÖTR"

            processed_content = raw_content.strip().upper()
            
            if "OLUMLU" in processed_content or "POZİTİF" in processed_content: return "OLUMLU"
            if "OLUMSUZ" in processed_content or "NEGATİF" in processed_content: return "OLUMSUZ"
            return "NÖTR" # Varsayılan

        except Exception as e:
            logger.error(f"LLM Hatası: {e}")
            return "ANALIZ_HATA"

    def search(self, company_name: str, start_date: str, end_date: str):
        """
        Tavily kullanarak şirket haberlerini arar.
        """
        # Tarih formatı dönüşümü
        tavily_start = self._format_date_for_tavily(start_date)
        tavily_end = self._format_date_for_tavily(end_date)
        
        logger.info(f"\n🚀 Tavily Aranıyor: {company_name}")
        logger.info(f"📅 Tarih: {tavily_start} - {tavily_end}")

        try:
            response = self.tavily_client.search(
                query=f"{company_name} şirketi ile ilgili haberler",
                search_depth="advanced",
                max_results=10,
                start_date=tavily_start,
                end_date=tavily_end,
                include_images=True,
                include_favicon=False,
                country="turkey"
            )
        except Exception as e:
            logger.error(f"Tavily API Hatası: {str(e)}")
            return {"error": str(e)}

        final_output = {
            "summary": f"{company_name} için arama sonuçları",
            "news_items": []
        }

        results_list = response.get("results", [])
        logger.info(f"📰 Toplam {len(results_list)} haber bulundu")

        for idx, item in enumerate(results_list, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("content", "")

            full_text = f"{title}. {content}"

            #if not self._is_relevant_to_company(full_text, company_name):
            #    continue
            
            # A. Haberin Kendi Görselini Çek (Scraping)
            # Tavily görsel dönse bile, sitenin meta taglerinden çekmek daha kalitelidir.
            article_image_url = self._get_article_image(url)
            local_image_path = None
            
            if article_image_url:
                local_image_path = self._download_image(article_image_url)
            
            # B. Duygu Analizi
            sentiment = self._analyze_sentiment(f"{title}. {content}")
            
            # C. Çıktı Ekleme
            # Not: Adapter yapısına uygun anahtar isimleri kullanıyoruz
            final_output["news_items"].append({
                "baslik": title,
                "link": url,
                "ozet": self._safe_truncate(content, 500),
                "duygu_analizi": sentiment,
                "skor": item.get("score"),
                "gorsel_yolu": local_image_path,
                "tarih": item.get("published_date") # Tavily bazen tarih döner
            })

        return final_output