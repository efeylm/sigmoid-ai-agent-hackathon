from sqlalchemy import Column, Integer, String, Text
import enum
from app.db import Base

class ChunkType(enum.Enum):
    NEWS = 1
    TRADE_REGISTRY = 2
    TENDER_BAN = 3

class Chunk(Base):
    __tablename__ = "chunks"

    # id = Column(Integer, primary_key=True, index=True)  <-- Removed
    chunk_code = Column(Integer, primary_key=True) 
    source_id = Column(Integer, primary_key=True)
    text_content = Column(Text)
    embedding_id = Column(String, nullable=True)