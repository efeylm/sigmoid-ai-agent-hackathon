# 🧪 Testing Guide

This project maintains a comprehensive integration test suite to ensure the reliability of the backend API and CRUD operations.

## 🚀 How to Run Tests

Tests are designed to run inside the Docker container to ensure they have access to the same environment and database connection as the application.

### Command
```bash
docker exec -i ai_agent_backend python3 -m pytest -v tests/
```

### Explanation
- `docker exec -i`: Executes a command interactively inside the running container.
- `ai_agent_backend`: The name of the backend service container.
- `python3 -m pytest`: Runs the pytest module (recommended over just `pytest` to handle paths correctly).
- `-v`: Verbose output to see individual test names.

## 📂 Test Structure

Tests are located in the `tests/` directory and mirror the `app/api/` structure.

| Test File | Description |
|-----------|-------------|
| [conftest.py](../tests/conftest.py) | **Configuration**: Sets up the `TestClient` and Database fixtures. Overrides the DB dependency to force a fresh session. |
| [test_companies.py](../tests/test_companies.py) | **Companies**: Verifies creation, listing, and retrieval by ID. |
| [test_queries.py](../tests/test_queries.py) | **Queries**: Verifies basic query creation logic. |
| [test_reports.py](../tests/test_reports.py) | **Reports**: verified full flow: Create Company -> Create Query -> Create Report linked to both. |
| [test_records.py](../tests/test_records.py) | **Records**: Verifies creation of News, Tender Ban, and Trade Registry records linked to reports. |
| [test_chunks.py](../tests/test_chunks.py) | **Chunks**: Verified the composite Primary Key logic `(chunk_code, source_id)` for creating and deleting chunks. |

## ✅ Current Status

**Last Run**: 2025-12-09
**Result**: 17/17 Tests Passed

| Test Case | Description | Status |
|-----------|-------------|--------|
| **Chunks** |
| `test_create_and_delete_chunk` | Create & Delete Chunk with Composite PK | ✅ PASS |
| **Companies** |
| `test_create_company` | Create Company | ✅ PASS |
| `test_read_companies` | List Companies | ✅ PASS |
| `test_read_company_by_id` | Get Company by ID | ✅ PASS |
| `test_update_company` | Update Company Name | ✅ PASS |
| `test_delete_company` | Delete Company | ✅ PASS |
| **Queries** |
| `test_create_query` | Create Query | ✅ PASS |
| `test_read_queries` | List Queries | ✅ PASS |
| `test_read_query_by_id` | Get Query by ID | ✅ PASS |
| **Records** |
| `test_create_news_record` | Create News Record | ✅ PASS |
| `test_create_tender_ban_record` | Create Tender Ban Record | ✅ PASS |
| `test_create_trade_registry_record` | Create Trade Registry Record | ✅ PASS |
| `test_get_records` | Get Records by ID (All Types) | ✅ PASS |
| `test_get_records_via_report_eager_loading` | Verify Records Eager Loading via Report | ✅ PASS |
| **Reports** |
| `test_create_report_full_flow` | Create Report with Relations | ✅ PASS |
| `test_update_report` | Update Report Fields | ✅ PASS |
| `test_delete_report` | Delete Report | ✅ PASS |
