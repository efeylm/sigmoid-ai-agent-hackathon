# Query Pydantic schemas
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class QueryBase(BaseModel):
    query_text: str

class QueryCreate(QueryBase):
    pass

class QueryResponse(QueryBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
