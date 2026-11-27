# FastAPI application entry point
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.logger import logger
from app.db import init_db, engine
from app.api import public, health, companies, reports, records, queries, chunks, auth
from app.security import require_access_code, access_code_required
from app.api.routers import news
# YENİ ROUTER'I IMPORT ET
from app.api.routers import intelligence
from app.api.routers import report  # New Router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting application...")
    init_db()
    logger.info("✅ Database initialized")
    yield
    # Shutdown
    logger.info("👋 Shutting down application...")
    engine.dispose()

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sigmoid AI Agent - Company Report Generation API",
    lifespan=lifespan,
    # Hide interactive docs when the API is locked with an access code
    docs_url=None if access_code_required() else "/docs",
    redoc_url=None if access_code_required() else "/redoc",
    openapi_url=None if access_code_required() else "/openapi.json",
)

# AI-generated: CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # Alternative port
        *[o.strip().rstrip("/") for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    ],
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Every /api route except /api/auth/status requires a valid access code
protected = [Depends(require_access_code)]
app.include_router(auth.router, prefix="/api")
app.include_router(health.router)
app.include_router(public.router, prefix="/api", dependencies=protected)
app.include_router(companies.router, prefix="/api", dependencies=protected)
app.include_router(reports.router, prefix="/api", dependencies=protected)
app.include_router(records.router, prefix="/api", dependencies=protected)
app.include_router(queries.router, prefix="/api", dependencies=protected)
app.include_router(chunks.router, prefix="/api", dependencies=protected)
app.include_router(news.router, prefix="/api", dependencies=protected)
# YENİ: SİCİL AGENT ENDPOINT'İNİ EKLE
# Artık /api/agent/sicil/generate-report adresinden ulaşılabilir olacak.
app.include_router(
    intelligence.router, 
    prefix="/api/intelligence",
    tags=["Company Intelligence Orchestrator"],
    dependencies=protected,
)

# NEW: AGENTIC REPORT ENDPOINT
app.include_router(
    report.router,
    prefix="/api/report",
    tags=["Agentic Report Generator"],
    dependencies=protected,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )



