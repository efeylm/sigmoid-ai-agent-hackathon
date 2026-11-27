
# app/models/trade_registry_record.py
from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.db import Base
from datetime import datetime


class TradeRegistryRecord(Base):
    __tablename__ = "trade_registry_records"

    id = Column(Integer, primary_key=True, index=True)
    # Hangi rapora ait olduğu
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    
    # Veriler
    summary = Column(Text)
    risk_score = Column(Integer, default=0)
    details = Column(JSON)  # analyzer.py'den gelen key-value'lar buraya
    
    # Metadata
    announcement_date = Column(String, nullable=True) # "21.11.2025" gibi
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler

    report = relationship("Report", back_populates="trade_registry_records")