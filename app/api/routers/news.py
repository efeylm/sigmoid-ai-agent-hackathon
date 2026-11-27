from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.agents.news.service import NewsAgentService
from app.agents.news.schemas import NewsSearchRequest, NewsResponse

router = APIRouter()

@router.post("/news/search", response_model=NewsResponse, tags=["News Agent"])
async def search_company_news(
    request: NewsSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Belirtilen şirket için haber araması yapar, sonuçları kaydeder ve döner.
    """
    service = NewsAgentService(db)
    try:
        return await service.search_and_save(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
