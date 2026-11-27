from fastapi.testclient import TestClient
import uuid

def test_create_and_delete_chunk(client: TestClient):
    uid = uuid.uuid4().hex
    # 1. Create Source (News)
    comp = client.post("/api/companies/", json={"name": f"Chunk Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"Chunk Q {uid}"}).json()
    report = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"]}).json()
    
    news = client.post(
        "/api/records/news",
        json={
            "report_id": report["id"],
            "headline": "Chunk News",
            "source_url": "http://chunk.com",
            "content": "Chunk Content",
            "publication_date": "2024-01-01",
            "sentiment": "POSITIVE"
        }
    ).json()
    
    source_id = news["id"]
    chunk_code = 1 # News
    
    # 2. Create Chunk
    response = client.post(
        "/api/chunks/",
        json={
            "chunk_code": chunk_code,
            "source_id": source_id,
            "text_content": "Chunk text",
            "embedding_id": "vec-1"
        }
    )
    assert response.status_code == 200
    assert response.json()["chunk_code"] == chunk_code
    
    # 3. Get Chunk
    get_res = client.get(f"/api/chunks/{chunk_code}/{source_id}")
    assert get_res.status_code == 200
    
    # 4. Delete Chunk
    del_res = client.delete(f"/api/chunks/{chunk_code}/{source_id}")
    assert del_res.status_code == 200
    
    # 5. Verify Deleted
    check_res = client.get(f"/api/chunks/{chunk_code}/{source_id}")
    assert check_res.status_code == 404
