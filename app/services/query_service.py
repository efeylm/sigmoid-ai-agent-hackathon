from app.models.query import Query
from app.schemas.query_schema import QueryCreate, QueryCreate as QueryUpdate
from app.services.base import CRUDBase

class CRUDQuery(CRUDBase[Query, QueryCreate, QueryUpdate]):
    pass

query = CRUDQuery(Query)
