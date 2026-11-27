from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Any, List
from .tools import scrape_sicil_gazetesi, ocr_sicil_documents
from .analyzer import analyze_text
import os
import traceback
from app.logger import logger

# --- 1. STATE TANIMI ---
# Liste yapısını koruyoruz.
class SicilState(TypedDict):
    company_name: str
    start_date: Optional[str]
    end_date: Optional[str]
    pdf_paths: List[str]           
    ocr_results: List[str]         
    analysis_results: List[Any]    
    error: Optional[str]

# --- 2. NODES ---

def scraper_node(state: SicilState):
    """1. Adım: Sicil gazetesini tara ve PDF listesini al"""
    logger.info(f"--- NODE: Scraper ({state['company_name']}) ---")
    
    try:
        # Tool'a argümanları invoke ile dictionary olarak geçiyoruz.
        # tools.py içindeki Input şeması bu key'leri bekliyor olmalı!
        tool_args = {
            "company_name": state["company_name"],
            "start_date": state.get("start_date"),
            "end_date": state.get("end_date")
        }
        
        # Scraper tool'unu çağırıyoruz
        paths = scrape_sicil_gazetesi.invoke(tool_args)
        
        if not paths:
            return {"error": "Sicil gazetesi taraması başarısız oldu veya kayıt bulunamadı."}
        
        logger.info(f"✅ Scraper Sonucu: {len(paths)} adet PDF bulundu.")
        return {"pdf_paths": paths}
        
    except Exception as e:
        logger.error(f"🔥 KRİTİK HATA (Scraper Node): {e}", exc_info=True)
        traceback.print_exc()
        return {"error": f"Scraper hatası: {str(e)}"}

def ocr_node(state: SicilState):
    """2. Adım: PDF Listesi üzerinde DÖNGÜ kurarak OCR yap"""
    logger.info("--- NODE: OCR (Batch) ---")
    pdf_paths = state.get("pdf_paths", [])
    
    if not pdf_paths:
        return {"error": "OCR yapılacak dosya listesi boş."}
    
    collected_texts = []
    
    for i, path in enumerate(pdf_paths):
        logger.info(f"   ↳ [{i+1}/{len(pdf_paths)}] OCR İşleniyor: {path}")
        
        if os.path.exists(path):
            try:
                text = ocr_sicil_documents.invoke(path)
                if text:
                    collected_texts.append(text)
                else:
                    logger.warning(f"      ⚠️ Boş OCR sonucu, atlandı.")
            except Exception as e:
                logger.error(f"      ❌ OCR Hatası ({path}): {e}")
        else:
            logger.error(f"      ❌ Dosya bulunamadı: {path}")
            
    logger.info(f"✅ OCR Tamamlandı. {len(collected_texts)} adet metin çıkarıldı.")
    
    if not collected_texts:
         return {"error": "Hiçbir dosyadan metin çıkarılamadı."}

    return {"ocr_results": collected_texts}

def analysis_node_func(state: SicilState):
    """3. Adım: Metin Listesi üzerinde DÖNGÜ kurarak Analiz yap"""
    logger.info("--- NODE: Analysis (Batch) ---")
    
    ocr_texts = state.get("ocr_results", [])
    company_name = state.get("company_name", "")
    
    if not ocr_texts:
        return {"error": "Analiz edilecek metin listesi boş."}
    
    final_analyses = []
    
    for i, text in enumerate(ocr_texts):
        logger.info(f"   ↳ [{i+1}/{len(ocr_texts)}] AI Analizi yapılıyor...")
        try:
            result = analyze_text(text, company_name)
            final_analyses.append(result)
        except Exception as e:
            logger.error(f"      🔥 Analiz hatası (Index {i}): {e}")
    
    logger.info(f"✅ Analiz Tamamlandı. {len(final_analyses)} adet rapor oluşturuldu.")
    return {"analysis_results": final_analyses}

# --- 3. EDGES & GRAPH ---

def check_scraper_success(state: SicilState):
    if state.get("error") or not state.get("pdf_paths"):
        return END
    return "ocr"

def check_ocr_success(state: SicilState):
    if state.get("error") or not state.get("ocr_results"):
        return END
    return "analyzer"

workflow = StateGraph(SicilState)

workflow.add_node("scraper", scraper_node)
workflow.add_node("ocr", ocr_node)
workflow.add_node("analyzer", analysis_node_func)

workflow.set_entry_point("scraper")

workflow.add_conditional_edges(
    "scraper",
    check_scraper_success,
    {"ocr": "ocr", END: END}
)

workflow.add_conditional_edges(
    "ocr",
    check_ocr_success,
    {"analyzer": "analyzer", END: END}
)

workflow.add_edge("analyzer", END)

sicil_app = workflow.compile()