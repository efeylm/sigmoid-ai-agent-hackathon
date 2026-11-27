from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.report_schema import ReportCreate, ReportResponse
from app.services.report_service import report

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/", response_model=List[ReportResponse])
def read_reports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve reports.
    """
    reports = report.get_multi(db, skip=skip, limit=limit)
    return reports

@router.post("/", response_model=ReportResponse)
def create_report(
    *,
    db: Session = Depends(get_db),
    report_in: ReportCreate,
) -> Any:
    """
    Create new report.
    """
    return report.create(db=db, obj_in=report_in)

@router.get("/{id}", response_model=ReportResponse)
def read_report(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Get report by ID.
    """
    report_obj = report.get(db=db, id=id)
    if not report_obj:
        raise HTTPException(status_code=404, detail="Report not found")
    return report_obj

@router.put("/{id}", response_model=ReportResponse)
def update_report(
    *,
    db: Session = Depends(get_db),
    id: int,
    report_in: ReportCreate,
) -> Any:
    """
    Update a report.
    """
    report_obj = report.get(db=db, id=id)
    if not report_obj:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.update(db=db, db_obj=report_obj, obj_in=report_in)

@router.delete("/{id}", response_model=ReportResponse)
def delete_report(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Delete a report.
    """
    report_obj = report.get(db=db, id=id)
    if not report_obj:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.remove(db=db, id=id)
