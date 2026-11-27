from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.query_schema import QueryCreate, QueryResponse
from app.services.query_service import query

router = APIRouter(prefix="/queries", tags=["queries"])

@router.get("/", response_model=List[QueryResponse])
def read_queries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve queries.
    """
    queries = query.get_multi(db, skip=skip, limit=limit)
    return queries

@router.post("/", response_model=QueryResponse)
def create_query(
    *,
    db: Session = Depends(get_db),
    query_in: QueryCreate,
) -> Any:
    """
    Create new query.
    """
    return query.create(db=db, obj_in=query_in)

@router.get("/{id}", response_model=QueryResponse)
def read_query(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """
    Get query by ID.
    """
    query_obj = query.get(db=db, id=id)
    if not query_obj:
        raise HTTPException(status_code=404, detail="Query not found")
    return query_obj
