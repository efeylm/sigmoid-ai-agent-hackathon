# Company SQLAlchemy model
# Database table definition for company entities
# Stores company information and metadata
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    # "Report" sınıfını import etmedik, string olarak belirttik.
    # Bu sayede circular import hatası almayız.
    reports = relationship("Report", back_populates="company")