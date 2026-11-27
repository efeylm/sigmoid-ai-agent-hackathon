from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.chunk_schema import ChunkCreate, ChunkResponse
from app.services.chunk_service import chunk

router = APIRouter(prefix="/chunks", tags=["chunks"])

@router.get("/", response_model=List[ChunkResponse])
def read_chunks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> Any:
    """
    Retrieve chunks.
    """
    return chunk.get_multi(db, skip=skip, limit=limit)

@router.post("/", response_model=ChunkResponse)
def create_chunk(
    *,
    db: Session = Depends(get_db),
    chunk_in: ChunkCreate,
) -> Any:
    """
    Create new chunk.
    """
    # Check if exists
    if chunk_in.chunk_code is not None and chunk_in.source_id is not None:
        existing = chunk.get(db, chunk_code=chunk_in.chunk_code, source_id=chunk_in.source_id)
        if existing:
             raise HTTPException(status_code=400, detail="Chunk with this code and source_id already exists")
    
    return chunk.create(db=db, obj_in=chunk_in)

@router.get("/{chunk_code}/{source_id}", response_model=ChunkResponse)
def read_chunk(
    *,
    db: Session = Depends(get_db),
    chunk_code: int,
    source_id: int,
) -> Any:
    """
    Get chunk by composite PK (chunk_code, source_id).
    """
    chunk_obj = chunk.get(db=db, chunk_code=chunk_code, source_id=source_id)
    if not chunk_obj:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk_obj

@router.delete("/{chunk_code}/{source_id}", response_model=ChunkResponse)
def delete_chunk(
    *,
    db: Session = Depends(get_db),
    chunk_code: int,
    source_id: int,
) -> Any:
    """
    Delete a chunk.
    """
    chunk_obj = chunk.get(db=db, chunk_code=chunk_code, source_id=source_id)
    if not chunk_obj:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk.remove(db=db, chunk_code=chunk_code, source_id=source_id)
