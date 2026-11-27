import json
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage
from app.llm import get_chat_llm
import os

from app.agents.state import MasterState
from app.agents.sicil_gazetesi.workflow import sicil_app
from app.logger import logger


#RESMİ GAZETE İÇİN AYRILMIŞ ALAN
def resmi_gazete_node(state: MasterState):
    """
    TODO: Resmi Gazete tarama işlemleri buraya eklenecek.
    Geliştirecek kişi:
    1. 'app/agents/resmi_gazete' klasörünü oluşturmalı.
    2. Buradan o workflow'u çağırmalı.
    3. Sonucu state['resmi_gazete_data'] içine yazmalı.
    """
    logger.info(f"⏳ [Orchestrator]: Resmi Gazete modülü henüz aktif değil. Atlanıyor... ({state['company_name']})")
    return {"resmi_gazete_data": []}

# Sicil Gazetesi için AYRILMIŞ ALAN
def sicil_wrapper_node(state: MasterState):
    logger.info(f"🏢 [Orchestrator]: Sicil Gazetesi işlemleri başlatılıyor... ({state['company_name']})")
    
    # Input hazırlığı
    sicil_input = {
        "company_name": state["company_name"],
        "start_date": state.get("start_date"),
        "end_date": state.get("end_date"),
        "pdf_paths": [],
        "ocr_results": [],
        "analysis_results": [] 
    }
    
    try:
        response_state = sicil_app.invoke(sicil_input)
    except Exception as e:
        error_msg = f"Sicil Agent Hatası: {str(e)}"
        logger.error(f"🔥 {error_msg}")
        return {"errors": [error_msg]}

    processed_records = []

    results = response_state.get("analysis_results", [])
    
    if results:
        logger.info(f"✅ Sicil modülünden {len(results)} adet analiz sonucu alındı.")
        
        for record in results:
            if hasattr(record, "dict"):
                record_dict = record.dict()
            elif hasattr(record, "model_dump"):
                record_dict = record.model_dump()
            else:
                record_dict = record

            summary = record_dict.get("summary", "")
            risk_score = record_dict.get("risk_score", 0)
            details_list = record_dict.get("details", [])
            
            if isinstance(details_list, list):
                details_json = {}
                for item in details_list:
                    if hasattr(item, "dict"): item = item.dict()
                    elif hasattr(item, "model_dump"): item = item.model_dump()
                    
                    key = item.get("key")
                    val = item.get("value")
                    if key:
                        details_json[key] = val
            else:
                details_json = details_list

            db_ready_obj = {
                "company_name": state["company_name"],
                "summary": summary,
                "risk_score": risk_score,
                "details_json": details_json, 
            }
            processed_records.append(db_ready_obj)
            logger.info(f"   💾 (Analiz Okundu): {summary[:40]}...")

    else:
        logger.warning("⚠️ Sicil verisi bulunamadı (Liste boş döndü).")
    
    return {"sicil_data": processed_records}

#WEB SEARCH İÇİN AYRILMIŞ ALAN
def web_search_node(state: MasterState):
    """
    TODO: Google/Bing search işlemleri buraya eklenecek.
    Geliştirecek kişi:
    1. 'app/agents/web_searcher' altında tool'ları yazmalı.
    2. Haberlerin sentiment analizini yapmalı.
    """
    logger.info("⏳ [Orchestrator]: Web arama modülü henüz aktif değil. Atlanıyor...")
    return {"web_search_data": []}

#FINAL REPORT İÇİN AYRILMIŞ ALAN
def reporter_node(state: MasterState):

    logger.info("📝 [Orchestrator]: Rapor oluşturuluyor...")
    
    llm = get_chat_llm(temperature=0)
    
    sicil_summary = json.dumps(state.get("sicil_data", []), indent=2, ensure_ascii=False)
    
    prompt_text = f"""
    Aşağıdaki şirket için toplanan istihbarat verilerini analiz et ve yönetici özeti çıkar.
    
    ŞİRKET: {state['company_name']}
    
    1. SİCİL GAZETESİ VERİLERİ (Doğrulanmış Resmi Kayıtlar):
    {sicil_summary}
    
    2. RESMİ GAZETE:
    (Veri yok - Modül geliştirme aşamasında)
    
    3. WEB HABERLERİ:
    (Veri yok - Modül geliştirme aşamasında)
    
    Lütfen şu başlıklarla bir rapor yaz:
    - Şirket Genel Görünümü
    - Son Sicil Hareketleri ve Anlamları
    - Tespit Edilen Riskler
    """
    
    try:
        response = llm.invoke([HumanMessage(content=prompt_text)])
        report_content = response.content
    except Exception as e:
        report_content = f"Rapor oluşturulurken hata oluştu: {e}"

    return {"final_report": report_content}


# --- GRAPH KURULUMU ---
workflow = StateGraph(MasterState)

# Node'ları ekle
workflow.add_node("resmi_gazete", resmi_gazete_node)
workflow.add_node("sicil_gazetesi", sicil_wrapper_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("reporter", reporter_node)

# Akışı Tanımla (Sıralı)
workflow.add_edge(START, "resmi_gazete")
workflow.add_edge("resmi_gazete", "sicil_gazetesi")
workflow.add_edge("sicil_gazetesi", "web_search")
workflow.add_edge("web_search", "reporter")
workflow.add_edge("reporter", END)

# Compile
master_app = workflow.compile()