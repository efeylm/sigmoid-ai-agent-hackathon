from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    final_summary = Column(Text, nullable=True)
    status = Column(Text, default="PROCESSING") # Servis kodunda bunu kullandığın için ekledim
    content = Column(Text, nullable=True)       # Servis kodunda content kullandığın için ekledim
    
    # Foreign Keys
    query_id = Column(Integer, ForeignKey("queries.id"), unique=True, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    # İlişkiler
    # Not: Query ve Company modellerini import etmediysen string referans ("Query") kullanmak doğrudur.
    query = relationship("Query", back_populates="report", lazy="joined")
    company = relationship("Company", back_populates="reports", lazy="joined")
    
    # Child İlişkiler
    news_records = relationship("NewsRecord", back_populates="report", lazy="selectin")
    
    # --- DÜZELTİLEN SATIR BURASI ---
    # Eski hali: registry_records = ...
    # Yeni hali: trade_registry_records = ...
    # Sebebi: TradeRegistryRecord modelindeki back_populates="trade_registry_records" burayı işaret ediyor.
    trade_registry_records = relationship("TradeRegistryRecord", back_populates="report", lazy="selectin")
    
    ban_records = relationship("TenderBanRecord", back_populates="report", lazy="selectin")