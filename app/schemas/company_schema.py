# Company Pydantic schemas
# Data Transfer Objects (DTOs) for company data validation
# Request and response models for company endpoints

from pydantic import BaseModel
from typing import Optional, List

class CompanyBase(BaseModel):
    name: str

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: int
    
    class Config:
        from_attributes = True
