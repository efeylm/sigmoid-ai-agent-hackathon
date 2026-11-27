# 📘 Backend System Summary & Developer Guide

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose

### Running the Application
Start the backend and database services:
```bash
docker-compose up -d --build
```

- **Backend API**: http://localhost:8000
- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Database Access
Connect to the running PostgreSQL container:
```bash
docker exec -it ai_agent_postgres psql -U postgres -d ai_agent_db
```

---

## 📡 API Endpoints & Usage

Data flow is usually: **Company -> Query -> Report -> Records**.

### 1. Companies (`/api/companies`)
Entities for which reports are generated.
- **POST /api/companies/**
  - Body: `{ "name": "Company Name" }`

### 2. Queries (`/api/queries`)
The user's input request/prompt.
- **POST /api/queries/**
  - Body: `{ "query_text": "Analyze risk for..." }`

### 3. Reports (`/api/reports`)
The central entity linking a Company and a Query to gathered Intelligence (Records).
- **POST /api/reports/**
  - Body: 
    ```json
    {
      "company_id": 1,
      "query_id": 1,
      "final_summary": "Optional summary..."
    }
    ```

### 4. Records (`/api/records`)
Raw data attached to a report. These are populated by agents.

#### News Records
- **POST /api/records/news**
  - Body:
    ```json
    {
      "report_id": 1,
      "headline": "Example News",
      "source_url": "http://example.com",
      "content": "Full text...",
      "publication_date": "2024-01-01",
      "sentiment": "POSITIVE"
    }
    ```

#### Tender Ban Records
- **POST /api/records/tender-bans**
  - Body:
    ```json
    {
      "report_id": 1,
      "banned_name": "Company Name",
      "legal_basis": "Law 4734",
      "ban_duration": "1 Year",
      "decision_ministry": "Ministry Name"
    }
    ```

#### Trade Registry Records
- **POST /api/records/trade-registry**
  - Body:
    ```json
    {
      "report_id": 1,
      "gazette_date": "2024-01-01",
      "mersis_no": "1234567890",
      "capital_amount": "1000000 TL"
    }
    ```

### 5. Chunks (`/api/chunks`)
Text chunks linked to specific source records.
- **POST /api/chunks/**
  - Body:
    ```json
    {
      "chunk_code": 1, 
      "source_id": 2,
      "text_content": "Content to embed...",
      "embedding_id": "optional-vector-id"
    }
    ```
  - **Logic**: `chunk_code` indicates source type (1: News, 2: Trade, 3: Ban). `source_id` is the PK of that source record.
- **GET /api/chunks/{chunk_code}/{source_id}**: Retrieve specific chunk.

---

## 📂 Project Structure

- **`app/models`**: SQLAlchemy database models (Table definitions).
- **`app/schemas`**: Pydantic models (Request/Response validation).
- **`app/api`**: FastAPI Routers (Endpoints).
- **`app/services`**: Business logic and CRUD operations.
- **`app/db.py`**: Database connection and session management.

## 🤝 For Frontend Developers
- **OpenAPI Schema**: `http://localhost:8000/openapi.json` (Can be used to generate clients).
- **Date Formats**: ISO 8601 strings are preferred.
- **Errors**: Standard HTTP 404/422/500 responses.

## 🤖 For Agent Developers
- **Populating Data**: Agents should write their findings to the `records` endpoints, linking them to a `report_id`.
- **Async Processing**: Currently synchronous, but designed to be called by an orchestrator or queue worker.
