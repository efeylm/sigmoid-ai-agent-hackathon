from fastapi.testclient import TestClient

def test_create_query(client: TestClient):
    response = client.post(
        "/api/queries/",
        json={"query_text": "What is the risk?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query_text"] == "What is the risk?"
    assert "id" in data

def test_read_queries(client: TestClient):
    client.post("/api/queries/", json={"query_text": "Q1"})
    res = client.get("/api/queries/")
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_read_query_by_id(client: TestClient):
    res = client.post("/api/queries/", json={"query_text": "Single Q"})
    qid = res.json()["id"]
    get_res = client.get(f"/api/queries/{qid}")
    assert get_res.status_code == 200
    assert get_res.json()["query_text"] == "Single Q"
