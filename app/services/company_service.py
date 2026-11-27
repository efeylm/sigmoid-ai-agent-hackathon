from app.models.company import Company
from app.schemas.company_schema import CompanyCreate, CompanyCreate as CompanyUpdate
from app.services.base import CRUDBase

class CRUDCompany(CRUDBase[Company, CompanyCreate, CompanyUpdate]):
    pass

company = CRUDCompany(Company)
