from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.db import get_db  # DB bağlantısı
from app.services.orchestrator_service import run_full_process
from app.security import limit_costly_request

router = APIRouter()

# --- Request Model ---
class IntelligenceRequest(BaseModel):
    company_name: str
    start_date: Optional[str] = Field(None, description="gg/aa/yyyy")
    end_date: Optional[str] = Field(None, description="gg/aa/yyyy")

# --- Response Model ---
class IntelligenceResponse(BaseModel):
    status: str
    process_id: str
    report_id: int
    final_report: Optional[str]
    data_count: int

@router.post("/analyze", response_model=IntelligenceResponse, dependencies=[Depends(limit_costly_request)])
async def analyze_company(
    request: IntelligenceRequest,
    db: Session = Depends(get_db) # <--- DB Session buraya eklendi
):
    try:
        # Servisi çağırırken db'yi gönderiyoruz
        result = await run_full_process(
            db=db, 
            company_name=request.company_name,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        return IntelligenceResponse(
            status=result["status"],
            process_id=result["process_id"],
            report_id=result["report_id"],
            final_report=result["final_report"],
            data_count=result["data_count"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))