# utils.py
import ddddocr
import re
import io
from PIL import Image

def solve_captcha_element(element_handle):
    """
    Playwright elementinden screenshot alır, görüntüyü temizler ve çözer.
    """
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    # 1. Ham resmi Playwright'tan al
    img_bytes = element_handle.screenshot()
    
    # 2. Görüntü İşleme (Image Processing)
    # Resmi bellekte aç
    image = Image.open(io.BytesIO(img_bytes))
    
    # Gri tona çevir (Grayscale)
    image = image.convert("L")
    
    # Siyah-Beyaz yap (Thresholding)
    # 160 değeri bir eşiktir. 160'tan koyu yerler siyah, açık yerler beyaz olur.
    # Bu işlem arkadaki gri çizgileri ve kenar gölgelerini uçurur.
    threshold = 150
    image = image.point(lambda p: 255 if p > threshold else 0)
    
    # (Opsiyonel) Eğer kenarlarda hala çizgi kalıyorsa biraz kırpabiliriz (Crop)
    # width, height = image.size
    # image = image.crop((2, 2, width-2, height-2)) # Her kenardan 2 piksel at
    
    # 3. İşlenmiş resmi tekrar byte'a çevir
    with io.BytesIO() as output:
        image.save(output, format="PNG")
        processed_bytes = output.getvalue()
    
    # 4. OCR'a sok
    raw_text = ocr.classification(processed_bytes)
    
    # Temizlik: Sadece harf ve rakamları al
    clean_text = re.sub(r'[^a-zA-Z0-9]', '', raw_text).upper()
    
    # --- KRİTİK MÜDAHALE ---
    # Bu sitedeki captchalar her zaman 4 hanelidir.
    # Eğer model 'MTY2V' gibi 5 hane bulduysa, sondaki o hayali harfi atıyoruz.
    if len(clean_text) > 4:
        clean_text = clean_text[:4]
        
    return clean_text