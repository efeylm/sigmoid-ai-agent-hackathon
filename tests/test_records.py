from fastapi.testclient import TestClient
import uuid

def test_create_news_record(client: TestClient):
    uid = uuid.uuid4().hex
    # Need a report first
    comp = client.post("/api/companies/", json={"name": f"News Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"News Q {uid}"}).json()
    report = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"]}).json()
    
    response = client.post(
        "/api/records/news",
        json={
            "report_id": report["id"],
            "headline": "Test News",
            "source_url": "http://test.com",
            "content": "Content",
            "publication_date": "2024-01-01",
            "sentiment": "POSITIVE"
        }
    )
    assert response.status_code == 200
    assert response.json()["headline"] == "Test News"

def test_create_tender_ban_record(client: TestClient):
    uid = uuid.uuid4().hex
    comp = client.post("/api/companies/", json={"name": f"Ban Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"Ban Q {uid}"}).json()
    report = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"]}).json()

    response = client.post(
        "/api/records/tender-bans",
        json={
            "report_id": report["id"],
            "banned_name": "Ban Inc",
            "legal_basis": "Law",
            "ban_duration": "1 Year"
        }
    )
    assert response.status_code == 200
    assert response.json()["banned_name"] == "Ban Inc"

def test_create_trade_registry_record(client: TestClient):
    uid = uuid.uuid4().hex
    comp = client.post("/api/companies/", json={"name": f"Trade Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"Trade Q {uid}"}).json()
    report = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"]}).json()

    response = client.post(
        "/api/records/trade-registry",
        json={
            "report_id": report["id"],
            "gazette_date": "2024-01-01",
            "mersis_no": "1234567890",
            "capital_amount": "100K"
        }
    )
    assert response.status_code == 200
    assert response.json()["mersis_no"] == "1234567890"

    assert response.status_code == 200
    assert response.json()["mersis_no"] == "1234567890"

    assert response.status_code == 200
    assert response.json()["mersis_no"] == "1234567890"

def test_get_records(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex
    
    # 1. News
    comp = client.post("/api/companies/", json={"name": f"GetRec Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"GetRec Q {uid}"}).json()
    report = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"]}).json()
    
    news = client.post("/api/records/news", json={
        "report_id": report["id"], "headline": f"H {uid}", "source_url": "u", "content": "c", "publication_date": "2024-01-01", "sentiment": "S"
    }).json()
    
    res = client.get(f"/api/records/news/{news['id']}")
    assert res.status_code == 200
    assert res.json()["headline"] == f"H {uid}"

    # 2. Tender Ban
    ban = client.post("/api/records/tender-bans", json={
        "report_id": report["id"], "banned_name": f"B {uid}", "legal_basis": "L", "ban_duration": "D"
    }).json()
    res = client.get(f"/api/records/tender-bans/{ban['id']}")
    assert res.status_code == 200
    assert res.json()["banned_name"] == f"B {uid}"

    # 3. Trade Registry
    trade = client.post("/api/records/trade-registry", json={
        "report_id": report["id"], "gazette_date": "d", "mersis_no": f"m{uid}", "capital_amount": "c"
    }).json()
    res = client.get(f"/api/records/trade-registry/{trade['id']}")
    assert res.status_code == 200
    assert res.json()["mersis_no"] == f"m{uid}"

def test_get_records_via_report_eager_loading(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex
    
    # 1. Setup Report
    comp = client.post("/api/companies/", json={"name": f"Eager Inc {uid}"}).json()
    q = client.post("/api/queries/", json={"query_text": f"Eager Q {uid}"}).json()
    report = client.post("/api/reports/", json={"company_id": comp["id"], "query_id": q["id"]}).json()
    rep_id = report["id"]

    # 2. Add Records
    client.post("/api/records/news", json={
        "report_id": rep_id, "headline": "News1", "source_url": "u", "content": "c", "publication_date": "2024-01-01", "sentiment": "S"
    })
    client.post("/api/records/tender-bans", json={
        "report_id": rep_id, "banned_name": "Ban1", "legal_basis": "L", "ban_duration": "D"
    })
    
    # 3. Fetch Report and Check Records are present
    # Accessing these fields would raise DetachedInstanceError if lazy loading was active and session closed
    # But since we use selectin, they should be present in the JSON response
    res = client.get(f"/api/reports/{rep_id}")
    assert res.status_code == 200
    data = res.json()
    
    assert len(data["news_records"]) == 1
    assert data["news_records"][0]["headline"] == "News1"
    
    assert len(data["ban_records"]) == 1
    assert data["ban_records"][0]["banned_name"] == "Ban1"
