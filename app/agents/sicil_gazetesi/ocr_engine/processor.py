import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageOps
import os
from app.logger import logger

# --- GÖRÜNTÜ İŞLEME VE İYİLEŞTİRME ---

def upscale_and_preprocess(img: Image.Image) -> Image.Image:
    """OCR başarısını artırmak için görüntüyü büyütür ve netleştirir."""
    w, h = img.size
    img = img.resize((w * 2, h * 2), resample=Image.LANCZOS)
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    return img

def clean_text(raw: str) -> str:
    """OCR çıktısındaki gereksiz boşlukları temizler."""
    lines = [line.rstrip() for line in raw.splitlines()]
    cleaned_lines = []
    buffer = ""
    for line in lines:
        s = line.strip()
        if not s:
            if buffer:
                cleaned_lines.append(buffer)
                buffer = ""
            continue
        if buffer.endswith("-"):
            buffer = buffer[:-1] + s
        else:
            if buffer:
                cleaned_lines.append(buffer)
            buffer = s
    if buffer:
        cleaned_lines.append(buffer)
    return "\n".join([" ".join(l.split()) for l in cleaned_lines])

# --- YENİ FORMAT (KUTULU) İÇİN FONKSİYONLAR ---

def find_boxes_in_page(img_pil: Image.Image):
    """
    Sayfa üzerindeki belirgin kutuları tespit eder.
    Hem sol hem sağ tarafı tek seferde analiz eder.
    """
    thresh = np.array(img_pil.convert("L"))
    blur = cv2.GaussianBlur(thresh, (5, 5), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Kutu tespiti için morfolojik işlem
    kernel = np.ones((5, 5), np.uint8)
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    contours, _ = cv2.findContours(morph, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    h_img, w_img = thresh.shape
    page_area = h_img * w_img
    boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        ratio = area / page_area
        
        # Filtreleme: Çok küçük, çok büyük veya çok ince kutuları at
        if ratio < 0.005 or ratio > 0.90: continue
        if w < w_img * 0.1: continue 
        if h < 40: continue

        boxes.append((x, y, w, h))
        
    return boxes

# --- ESKİ FORMAT (SÜTUNLU) İÇİN FONKSİYONLAR ---

def get_column_slices(img_pil: Image.Image):
    """
    Sayfadaki dikey siyah çizgileri tespit eder ve sayfayı sütunlara böler.
    Dikey çizgi bulamazsa, sayfayı eşit 5 parçaya böler (Backup Plan).
    """
    # OpenCV formatına çevir
    img_cv = np.array(img_pil.convert("L"))
    h, w = img_cv.shape

    # 1. Dikey Çizgileri Bul (Vertical Line Detection)
    # Thresholding
    _, binary = cv2.threshold(img_cv, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Dikey çekirdek (Kernel): Yatay detayları yok et, sadece dikey uzun çizgileri tut
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 30))
    detected_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    
    # Çizgilerin X koordinatlarını bul
    # Sütun toplamı al -> 0 olmayan yerler çizgi var demektir
    col_sum = np.sum(detected_lines, axis=0)
    
    # Çizgi olan x noktalarını bul (Basit peak detection)
    x_indices = np.where(col_sum > (h * 0.2 * 255))[0] # Sayfanın %20'si kadar uzunluğu olan çizgiler
    
    cut_points = [0] # Başlangıç noktası
    
    if len(x_indices) > 0:
        # Yakın çizgileri grupla (çizgi kalınlığı birden fazla piksel olabilir)
        unique_x = []
        if len(x_indices) > 0:
            current_group = [x_indices[0]]
            for i in range(1, len(x_indices)):
                if x_indices[i] - x_indices[i-1] < 15: # 15 piksel tolerans
                    current_group.append(x_indices[i])
                else:
                    unique_x.append(int(np.mean(current_group)))
                    current_group = [x_indices[i]]
            unique_x.append(int(np.mean(current_group)))
        
        # Kesim noktalarını ekle
        cut_points.extend(unique_x)
    
    cut_points.append(w) # Bitiş noktası
    cut_points = sorted(list(set(cut_points)))

    slices = []
    
    # Eğer tespit edilen sütun sayısı çok azsa (Örn: sadece sol ve sağ kenar),
    # görüntü işleme başarısız olmuş olabilir. Bu durumda "Brute Force" 5'e böl.
    # Genelde 1 çizgi bulsa bile 2 sütun yapar. Biz en az 3 sütun bekliyoruz eski formatta.
    if len(cut_points) < 4: 
        logger.warning("   ⚠️ Net dikey çizgiler bulunamadı. Standart 5 sütunlu yapı varsayılıyor.")
        col_width = w // 5
        cut_points = [0, col_width, col_width*2, col_width*3, col_width*4, w]

    # Dilimleme işlemi
    for i in range(len(cut_points) - 1):
        x1 = cut_points[i]
        x2 = cut_points[i+1]
        
        # Çok dar dilimleri atla (Gürültü veya kenar boşluğu)
        if (x2 - x1) < 50: continue
        
        # Kırpma (Biraz pay bırakarak - padding yok, içerik karışmasın)
        slice_img = img_pil.crop((x1, 0, x2, h))
        slices.append(slice_img)
        
    return slices

# --- ANA İŞLEMCİ ---

def extract_text_from_pdf(pdf_path: str) -> str:
    logger.info(f"📄 İşlem Başlıyor: {pdf_path}")
    
    try:
        pages = convert_from_path(pdf_path, dpi=300) # 400 çok yavaş olabilir, 300 genelde yeterli
        full_text_blocks = []

        for page_index, page_img in enumerate(pages):
            w, h = page_img.size
            
            # --- STRATEJİ BELİRLEME ---
            # Önce kutu var mı diye bak.
            found_boxes = find_boxes_in_page(page_img)
            
            # Kutu sayısı eşiği. Yeni formatta genellikle en az 4-5 kutu olur.
            # Eski formatta da çizgiler bazen kutu gibi algılanabilir ama sayıları az olur veya çok ince uzun olurlar.
            is_new_format = len(found_boxes) > 4
            
            if is_new_format:
                logger.info(f"   ► Sayfa {page_index+1}: YENİ FORMAT (Kutulu) algılandı. ({len(found_boxes)} kutu)")
                
                # Kutuları sıralama mantığı:
                # Önce Y eksenine göre kabaca grupla, sonra X eksenine göre (Sol -> Sağ)
                # Ancak senin senaryonda genelde 2 ana sütun var.
                mid_x = w // 2
                def sort_boxes(box):
                    x, y, bw, bh = box
                    # Hangi ana sütunda? Sol mu Sağ mı?
                    col_id = 0 if (x + bw/2) < mid_x else 1
                    return (col_id, y) # Önce sütun, sonra yukarıdan aşağı
                
                found_boxes.sort(key=sort_boxes)
                
                for box in found_boxes:
                    bx, by, bw, bh = box
                    crop = page_img.crop((bx, by, bx+bw, by+bh))
                    crop = ImageOps.expand(crop, border=10, fill='white')
                    
                    processed = upscale_and_preprocess(crop)
                    # PSM 6: Bloğu tek bir metin bloğu olarak gör
                    raw = pytesseract.image_to_string(processed, lang="tur", config="--oem 1 --psm 6")
                    clean = clean_text(raw)
                    if len(clean) > 5:
                        full_text_blocks.append(clean)
                        
            else:
                logger.info(f"   ► Sayfa {page_index+1}: ESKİ FORMAT (Sütunlu) algılandı.")
                column_images = get_column_slices(page_img)
                logger.info(f"     ↳ Sayfa {len(column_images)} sütuna bölündü.")
                
                # 3. Sırayla OCR Yap (Soldan Sağa)
                for i, col_img in enumerate(column_images):
                    processed = upscale_and_preprocess(col_img)
                    
                    # PSM 4 veya 6 kullanılabilir. 
                    # PSM 4: Tek bir sütun olduğunu varsay (Column mode).
                    raw = pytesseract.image_to_string(processed, lang="tur", config="--oem 1 --psm 4")
                    clean = clean_text(raw)
                    
                    if len(clean) > 10:
                        full_text_blocks.append(f"\n--- Sütun {i+1} ---\n{clean}")

        final_output = "\n\n" + ("="*50) + "\n\n".join(full_text_blocks)
        return final_output

    except Exception as e:
        logger.error(f"❌ Kritik Hata: {e}")
        return ""