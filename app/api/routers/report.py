from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import os
import logging
from typing import List, Optional
from datetime import datetime

from app.db import get_db
from app.agents.report_agent import ReportAgent, SearchAgentType
from app.services.pdf_service import PDFService
from app.security import limit_costly_request

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

class ReportRequest(BaseModel):
    company_name: str
    start_date: str = Field(..., description="Start date in DD/MM/YYYY format")
    end_date: str = Field(..., description="End date in DD/MM/YYYY format")
    agent_type: SearchAgentType = Field(..., description="Search agent type: 'TAVILY' or 'GOOGLE'")

# Response schema'ları
class ReportListItem(BaseModel):
    id: int
    company_name: str
    status: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True  # SQLAlchemy model desteği için

class ReportListResponse(BaseModel):
    reports: List[ReportListItem]
    total: int

def remove_file(path: str):
    """Deletes the temporary file."""
    try:
        os.remove(path)
    except Exception:
        pass

@router.post("/generate", response_class=FileResponse, dependencies=[Depends(limit_costly_request)])
async def generate_agentic_report(
    request: ReportRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generates a company report using an AI agent and returns it as a fancy PDF.
    Also saves news and sicil records to the database.
    """
    logger.info(f"🚀 Report generation started for {request.company_name} ({request.start_date}-{request.end_date}) using {request.agent_type}")
    try:
        # 1. Generate Report Content (Markdown) & Save to DB
        logger.info("🤖 Initializing ReportAgent...")
        agent = ReportAgent(db=db)
        
        # Agent generates report AND saves records to DB internally
        result = await agent.generate_report(
            company_name=request.company_name,
            start_date=request.start_date,
            end_date=request.end_date,
            agent_type=request.agent_type
        )
        
        report_content = result["report_content"]
        logger.info(f"✅ Report content generated (Length: {len(report_content)} chars)")
        logger.info(f"📊 Stats: {result['news_count']} news, {result['sicil_count']} sicil records saved.")
        
        # 2. Convert to PDF
        logger.info("📄 Converting content to PDF...")
        pdf_path = PDFService.generate_pdf_report(report_content, request.company_name, image_base_path="/app")
        
        # 3. Schedule cleanup
        background_tasks.add_task(remove_file, pdf_path)
        logger.info(f"✅ PDF generated at: {pdf_path}")
        
        # 4. Return PDF File
        filename = f"{request.company_name.replace(' ', '_')}_Report.pdf"
        return FileResponse(
            path=pdf_path, 
            filename=filename, 
            media_type='application/pdf'
        )

    except Exception as e:
        logger.error(f"🔥 Error generating report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# GET endpoint - Tüm raporları listele
@router.get("/list", response_model=ReportListResponse)
async def list_reports(db: Session = Depends(get_db)):
    """
    Veritabanındaki tüm raporları listeler.
    """
    from app.models.report import Report
    from app.models.company import Company
    
    reports = db.query(Report).join(Company).all()
    
    report_items = [
        ReportListItem(
            id=r.id,
            company_name=r.company.name,
            status=r.status,
            created_at=r.created_at
        )
        for r in reports
    ]
    
    return ReportListResponse(reports=report_items, total=len(report_items))

# GET endpoint - Belirli bir raporu getir
@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """
    Belirli bir raporun detaylarını getirir.
    """
    from app.models.report import Report
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")
    
    return {
        "id": report.id,
        "company_name": report.company.name,
        "status": report.status,
        "content": report.content,
        "final_summary": report.final_summary,
        "created_at": report.created_at
    } 

# app/api/routers/report.py'ye eklenecek

@router.get("/{report_id}/pdf", response_class=FileResponse)
async def get_report_pdf(
    report_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Kayıtlı bir raporun PDF'ini döndürür.
    """
    from app.models.report import Report
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")
    
    if not report.content:
        raise HTTPException(status_code=404, detail="Rapor içeriği bulunamadı")
    
    # PDF oluştur
    pdf_path = PDFService.generate_pdf_report(report.content, report.company.name, image_base_path="/app")
    
    # Cleanup planla
    background_tasks.add_task(remove_file, pdf_path)
    
    filename = f"{report.company.name.replace(' ', '_')}_Report.pdf"
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type='application/pdf'
    )
