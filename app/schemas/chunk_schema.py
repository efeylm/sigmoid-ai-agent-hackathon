# Chunk Pydantic schemas
from pydantic import BaseModel
from typing import Optional

class ChunkBase(BaseModel):
    chunk_code: Optional[int] = None
    source_id: Optional[int] = None
    text_content: Optional[str] = None
    embedding_id: Optional[str] = None

class ChunkCreate(ChunkBase):
    pass

class ChunkResponse(ChunkBase):
    chunk_code: int
    source_id: int

    class Config:
        from_attributes = True
