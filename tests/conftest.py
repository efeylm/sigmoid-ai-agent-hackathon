import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db import Base, get_db
from app.config import settings

# Test DB Setup
# Using the same database URL but ensuring we are careful with data
# In a real scenario, use a separate test database
engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db() -> Generator[Session, None, None]:
    # Use the existing DB, ensuring tables exist
    # Base.metadata.create_all(bind=engine) # Tables already exist via docker
    yield TestingSessionLocal()
    
@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    # Override get_db dependency to use the unique TestingSessionLocal
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
