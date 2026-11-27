# FastAPI application entry point
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.logger import logger
from app.db import init_db, engine
from app.api import public, health, companies, reports, records, queries, chunks
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
    lifespan=lifespan
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
app.include_router(health.router)
app.include_router(public.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(queries.router, prefix="/api")
app.include_router(chunks.router, prefix="/api")
app.include_router(news.router, prefix="/api")
# YENİ: SİCİL AGENT ENDPOINT'İNİ EKLE
# Artık /api/agent/sicil/generate-report adresinden ulaşılabilir olacak.
app.include_router(
    intelligence.router, 
    prefix="/api/intelligence", 
    tags=["Company Intelligence Orchestrator"]
)

# NEW: AGENTIC REPORT ENDPOINT
app.include_router(
    report.router,
    prefix="/api/report",
    tags=["Agentic Report Generator"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )



