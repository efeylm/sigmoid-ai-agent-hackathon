from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base

class NewsRecord(Base):
    __tablename__ = "news_records"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    
    source_url = Column(String)
    headline = Column(String)
    content = Column(Text)
    publication_date = Column(String)
    sentiment = Column(String)
    image_path = Column(String)
    
    report = relationship("Report", back_populates="news_records")