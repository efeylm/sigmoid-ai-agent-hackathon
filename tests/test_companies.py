from fastapi.testclient import TestClient
import uuid

def test_create_company(client: TestClient):
    uid = uuid.uuid4().hex
    name = f"Test Company {uid}"
    response = client.post(
        "/api/companies/",
        json={"name": name}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert "id" in data

def test_read_companies(client: TestClient):
    response = client.get("/api/companies/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_read_company_by_id(client: TestClient):
    # First create
    uid = uuid.uuid4().hex
    name = f"Read Me Inc {uid}"
    res = client.post("/api/companies/", json={"name": name})
    company_id = res.json()["id"]
    
    response = client.get(f"/api/companies/{company_id}")
    assert response.status_code == 200
    assert response.json()["name"] == name

def test_update_company(client: TestClient):
    # 1. Create
    import uuid
    uid = uuid.uuid4().hex
    res = client.post("/api/companies/", json={"name": f"Old Name {uid}"})
    company_id = res.json()["id"]

    # 2. Update
    update_res = client.put(f"/api/companies/{company_id}", json={"name": f"New Name {uid}"})
    assert update_res.status_code == 200
    assert update_res.json()["name"] == f"New Name {uid}"

    # 3. Verify
    get_res = client.get(f"/api/companies/{company_id}")
    assert get_res.json()["name"] == f"New Name {uid}"

def test_delete_company(client: TestClient):
    # 1. Create
    import uuid
    uid = uuid.uuid4().hex
    res = client.post("/api/companies/", json={"name": f"Delete Me {uid}"})
    company_id = res.json()["id"]

    # 2. Delete
    del_res = client.delete(f"/api/companies/{company_id}")
    assert del_res.status_code == 200
    
    # 3. Verify Gone
    get_res = client.get(f"/api/companies/{company_id}")
    assert get_res.status_code == 404
