from app.models.report import Report
from app.schemas.report_schema import ReportCreate, ReportCreate as ReportUpdate
from app.services.base import CRUDBase

class CRUDReport(CRUDBase[Report, ReportCreate, ReportUpdate]):
    pass

report = CRUDReport(Report)
