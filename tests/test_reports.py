from fastapi.testclient import TestClient
import uuid

def test_create_report_full_flow(client: TestClient):
    uid = uuid.uuid4().hex
    # 1. Create Company
    comp = client.post("/api/companies/", json={"name": f"Report Inc {uid}"}).json()
    
    # 2. Create Query
    q = client.post("/api/queries/", json={"query_text": f"Report Query {uid}"}).json()
    
    # 3. Create Report
    response = client.post(
        "/api/reports/",
        json={
            "company_id": comp["id"],
            "query_id": q["id"],
            "final_summary": "Test Summary"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == comp["id"]
    assert data["query_id"] == q["id"]
    
    # 4. Get Report
    repo_id = data["id"]
    get_res = client.get(f"/api/reports/{repo_id}")
    assert get_res.status_code == 200
    assert get_res.json()["company"]["name"] == f"Report Inc {uid}"

def test_update_report(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex
    # Setup
    comp = client.post("/api/companies/", json={"name": f"Upd Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"Upd Q {uid}"}).json()
    repo = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"], "final_summary": "Old"}).json()
    
    # Update
    repo_id = repo["id"]
    res = client.put(f"/api/reports/{repo_id}", json={"final_summary": "Updated Summary"})
    assert res.status_code == 200
    assert res.json()["final_summary"] == "Updated Summary"

def test_delete_report(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex
    # Setup
    comp = client.post("/api/companies/", json={"name": f"Del Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"Del Q {uid}"}).json()
    # Ensure creation worked
    assert "id" in comp, f"Company creation failed: {comp}"
    assert "id" in q, f"Query creation failed: {q}"
    
    repo_res = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"]})
    assert repo_res.status_code == 200
    repo = repo_res.json()
    
    repo_id = repo["id"]
    del_res = client.delete(f"/api/reports/{repo_id}")
    assert del_res.status_code == 200
    
    # Verify
    assert client.get(f"/api/reports/{repo_id}").status_code == 404
