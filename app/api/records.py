from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.news_record_schema import NewsRecordCreate, NewsRecordResponse
from app.schemas.tender_ban_record_schema import TenderBanRecordCreate, TenderBanRecordResponse
from app.schemas.trade_registry_record_schema import TradeRegistryRecordCreate, TradeRegistryRecordResponse
from app.services.record_service import news_record, tender_ban_record, trade_registry_record

router = APIRouter(prefix="/records", tags=["records"])

# --- News Records ---
@router.post("/news", response_model=NewsRecordResponse)
def create_news_record(
    *,
    db: Session = Depends(get_db),
    item_in: NewsRecordCreate,
) -> Any:
    return news_record.create(db=db, obj_in=item_in)

@router.get("/news/{id}", response_model=NewsRecordResponse)
def read_news_record(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    item = news_record.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="News record not found")
    return item

# --- Tender Ban Records ---
@router.post("/tender-bans", response_model=TenderBanRecordResponse)
def create_tender_ban_record(
    *,
    db: Session = Depends(get_db),
    item_in: TenderBanRecordCreate,
) -> Any:
    return tender_ban_record.create(db=db, obj_in=item_in)

@router.get("/tender-bans/{id}", response_model=TenderBanRecordResponse)
def read_tender_ban_record(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    item = tender_ban_record.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Tender ban record not found")
    return item

# --- Trade Registry Records ---
@router.post("/trade-registry", response_model=TradeRegistryRecordResponse)
def create_trade_registry_record(
    *,
    db: Session = Depends(get_db),
    item_in: TradeRegistryRecordCreate,
) -> Any:
    return trade_registry_record.create(db=db, obj_in=item_in)

@router.get("/trade-registry/{id}", response_model=TradeRegistryRecordResponse)
def read_trade_registry_record(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    item = trade_registry_record.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Trade registry record not found")
    return item
