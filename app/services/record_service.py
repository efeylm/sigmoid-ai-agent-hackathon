from app.models.news_record import NewsRecord
from app.models.tender_ban_record import TenderBanRecord
from app.models.trade_registry_record import TradeRegistryRecord
from app.schemas.news_record_schema import NewsRecordCreate, NewsRecordCreate as NewsRecordUpdate
from app.schemas.tender_ban_record_schema import TenderBanRecordCreate, TenderBanRecordCreate as TenderBanRecordUpdate
from app.schemas.trade_registry_record_schema import TradeRegistryRecordCreate, TradeRegistryRecordCreate as TradeRegistryRecordUpdate
from app.services.base import CRUDBase

class CRUDNewsRecord(CRUDBase[NewsRecord, NewsRecordCreate, NewsRecordUpdate]):
    pass

class CRUDTenderBanRecord(CRUDBase[TenderBanRecord, TenderBanRecordCreate, TenderBanRecordUpdate]):
    pass

class CRUDTradeRegistryRecord(CRUDBase[TradeRegistryRecord, TradeRegistryRecordCreate, TradeRegistryRecordUpdate]):
    pass

news_record = CRUDNewsRecord(NewsRecord)
tender_ban_record = CRUDTenderBanRecord(TenderBanRecord)
trade_registry_record = CRUDTradeRegistryRecord(TradeRegistryRecord)
