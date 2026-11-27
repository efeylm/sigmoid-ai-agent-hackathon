from app.llm import get_chat_llm
from langchain_core.prompts import ChatPromptTemplate
from .schemas import SicilAnalysisResult
import os

# --- GÜÇLENDİRİLMİŞ PROMPT ---
# Bu prompt, metin içindeki gürültüyü filtreler ve hedef şirkete kilitlenir.

ANALYSIS_PROMPT = """
Sen uzman bir Ticaret Sicil Gazetesi Analistisin. Görevin, karmaşık ve birleştirilmiş OCR metinleri içerisinden
HEDEF ŞİRKET ile ilgili olan İLANI bulmak ve bu ilanı ayrıntılı şekilde analiz etmektir.

HEDEF ŞİRKET İSMİ: "{target_company}"

GİRDİ METNİ:
{ocr_text}

--- GENEL KURALLAR ---

• Yalnızca HEDEF ŞİRKET ile ilgili ilan bloğunu dikkate al.
• Çıktın SicilAnalysisResult şemasına uygun olsun:
  - summary: İlanın 1 cümlelik özeti.
  - details: key–value çiftlerinden oluşan liste (başlık ve cevabı).
  - risk_score: 0–100 arası sayısal risk skoru (genelde 0 bırakılabilir).

--- 1. İLGİLİ BLOĞU BUL ---

1. Metin içinde "{target_company}" ismine en çok benzeyen (fuzzy match) ilanı tespit et.
   - İlanlar genellikle "T.C. ... TİCARET SİCİLİ MÜDÜRLÜĞÜ'NDEN" ile başlar.
   - Aynı metinde başka şirketler de olabilir; HEDEF ŞİRKET dışındaki ilanları tamamen YOK SAY.

--- 2. VERİ ÇIKARIMI: ZORUNLU VE OPSİYONEL BAŞLIKLAR ---

### ⚠️ ZORUNLU BAŞLIKLAR (Bu 5 başlık MUTLAKA details listesinde olmalı)

Aşağıdaki 5 başlık, her zaman "details" listesine EKLENMELİDİR.
Metinde açıkça bulunamazsa, "value" alanına "Belirtilmemiş" yaz.

| Sıra | Başlık (key)    | Açıklama                                                                 |
|------|-----------------|--------------------------------------------------------------------------|
| 1    | Tescil Tarihi   | İlanın tescil edildiği tarih (genellikle "Tescil Tarihi:" satırında)     |
| 2    | Gazete Tarihi   | Sicil Gazetesi'nin yayınlandığı tarih (genellikle sayfa üstünde)         |
| 3    | Gazete Sayısı   | Sicil Gazetesi'nin sayı numarası (genellikle "Sayı: XXXXX" formatında)   |
| 4    | Firma Ünvanı    | Şirketin tam ticari unvanı (A.Ş., Ltd. Şti. vb. dahil)                   |
| 5    | İlan Konusu     | Tescil/ilan konusu (Kuruluş, Sermaye Artırımı, Adres Değişikliği vb.)    |

### 📋 OPSİYONEL BAŞLIKLAR (Metinde varsa ekle, yoksa ekleme)

Aşağıdaki başlıkları, YALNIZCA metinde ilgili bilgi varsa "details" listesine ekle:

• Toplantı Türü (Olağan / Olağanüstü)
• Toplantı Tarihi
• Toplantı Saati
• Toplantı Yeri (açık adres)
• Hesap Dönemi (ör: 01.01.2008–31.12.2008)
• Gündem Özeti (kısa metin)
• Gündem Maddesi Sayısı
• Gündem 1, Gündem 2, Gündem 3, ... (maddeler çok uzunsa kısaltılmış özetler ver)
• Mersis Numarası
• Ticaret Sicil Numarası
• Vergi Kimlik Numarası
• Şirket Merkezi Adresi
• Eski Adres / Yeni Adres (Adres değişikliği varsa)
• Eski Sermaye / Yeni Sermaye (Sermaye değişikliği varsa)
• Pay Sahipleri / Ortaklar
• Yönetim Kurulu Üyeleri
• Müdürler / Yetkili Temsilciler
• İmza Yetkisi
• Faaliyet Konusu
• Katılım Şartları / Bilgi Notu Özeti
• Hamiline / Nama Hisse Sahiplerinden İstenen Belgeler
• Vekaletname ile Temsil Şartları
• Bağımsız Denetçi / Denetim Kuruluşu Seçimi (varsa)
• Yönetim Kurulu Üyeleriyle İlgili Kararlar (seçim, azil, ücret vb. varsa)
• Denetçilerle İlgili Kararlar (seçim, azil, ücret vb. varsa)
• Bağış ve Yardımların Sunumu (varsa)
• İlanı Yapan Organ (ör: İdare Meclisi, Yönetim Kurulu)

--- 3. DETAY KURALLARI ---

DETAY SAYISI:
• "details" listesinde ZORUNLU 5 başlık + en az 2-5 opsiyonel başlık olmak üzere **EN AZ 7 FARKLI BAŞLIK** olsun.
• Uygunsa 10–20 arası başlık üret.
• Her başlık benzersiz ve anlamlı olsun; aynı bilgiyi farklı kelimelerle tekrar etme.

BAŞLIK KALİTESİ:
• "key" alanı kısa ve anlaşılır bir başlık olsun (ör: "Toplantı Tarihi", "Toplantı Yeri").
• "value" alanı, mümkün olduğunca tam ve okunabilir cümle ya da özet bilgi olsun.
• Tarih, saat, adres gibi alanlarda mümkünse orijinal formatı (gün/ay/yıl, saat) koru.

SIRALAMA:
• "details" listesinde önce 5 ZORUNLU başlığı sırayla ver, sonra opsiyonel başlıkları ekle.

--- 4. ÖZET (summary) ---

• summary alanında, ilanı 1 cümlede toparlayan net bir özet ver.
  Örn: "Bim Birleşik Mağazalar A.Ş.'nin 24 Nisan 2009 tarihinde İstanbul Samandıra'da yapılacak 2008 yılına ilişkin Olağan Genel Kurul toplantısına davet ilanıdır."

--- 5. HEDEF ŞİRKET BULUNAMAZSA ---

Eğer metinde HEDEF ŞİRKET ile ilgili ilan bulamazsan:
• summary: "İlgili şirket kaydı metin içinde tespit edilemedi." yaz.
• details: Yalnızca 5 zorunlu başlığı "Belirtilmemiş" değeriyle döndür.
• risk_score: 0 bırak.
"""


def analyze_text(ocr_text: str, target_company: str):
    """
    OCR metnini ve aranacak şirket ismini alır.
    """

    llm = get_chat_llm(temperature=0)

    structured_llm = llm.with_structured_output(SicilAnalysisResult)

    prompt = ChatPromptTemplate.from_template(ANALYSIS_PROMPT)
    chain = prompt | structured_llm

    # target_company parametresini prompt'a paslıyoruz
    result = chain.invoke({
        "ocr_text": ocr_text,
        "target_company": target_company
    })
    
    return result