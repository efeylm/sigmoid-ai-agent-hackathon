from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.schemas.chunk_schema import ChunkCreate, ChunkCreate as ChunkUpdate
from app.services.base import CRUDBase

class CRUDChunk(CRUDBase[Chunk, ChunkCreate, ChunkUpdate]):
    def get(self, db: Session, chunk_code: int, source_id: int) -> Optional[Chunk]:
        return db.query(self.model).filter(
            self.model.chunk_code == chunk_code,
            self.model.source_id == source_id
        ).first()

    def remove(self, db: Session, *, chunk_code: int, source_id: int) -> Chunk:
        obj = self.get(db, chunk_code=chunk_code, source_id=source_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Chunk,
        obj_in: ChunkUpdate | dict[str, Any]
    ) -> Chunk:
        return super().update(db, db_obj=db_obj, obj_in=obj_in)

chunk = CRUDChunk(Chunk)
