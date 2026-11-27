from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.company_schema import CompanyCreate, CompanyResponse
from app.services.company_service import company

router = APIRouter(prefix="/companies", tags=["companies"])

@router.get("/", response_model=List[CompanyResponse])
def read_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve companies.
    """
    companies = company.get_multi(db, skip=skip, limit=limit)
    return companies

@router.post("/", response_model=CompanyResponse)
def create_company(
    *,
    db: Session = Depends(get_db),
    company_in: CompanyCreate,
) -> Any:
    """
    Create new company.
    """
    return company.create(db=db, obj_in=company_in)

@router.get("/{id}", response_model=CompanyResponse)
def read_company(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Get company by ID.
    """
    company_obj = company.get(db=db, id=id)
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return company_obj

@router.put("/{id}", response_model=CompanyResponse)
def update_company(
    *,
    db: Session = Depends(get_db),
    id: int,
    company_in: CompanyCreate,
) -> Any:
    """
    Update a company.
    """
    company_obj = company.get(db=db, id=id)
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return company.update(db=db, db_obj=company_obj, obj_in=company_in)

@router.delete("/{id}", response_model=CompanyResponse)
def delete_company(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Delete a company.
    """
    company_obj = company.get(db=db, id=id)
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")
    return company.remove(db=db, id=id)
