import io
import pytest

def test_paste_text_document(client, auth_headers):
    resp = client.post("/api/documents/paste", json={
        "title": "Corporate Holiday Calendar 2026",
        "department": "HR",
        "raw_text": "The company observes 12 paid holidays in 2026. Independence Day is observed on July 4th.",
        "permitted_principals": ["general_employee", "hr_manager"]
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Corporate Holiday Calendar 2026"
    assert data["indexing_status"] == "ready"
    assert "general_employee" in data["permitted_principals"]

def test_empty_document_rejected(client, auth_headers):
    resp = client.post("/api/documents/paste", json={
        "title": "Empty Document",
        "department": "General",
        "raw_text": "   ",
        "permitted_principals": ["general_employee"]
    }, headers=auth_headers)
    assert resp.status_code == 400

def test_document_detail_and_chunks(client, auth_headers):
    # Ingest document
    resp = client.post("/api/documents/paste", json={
        "title": "API Gateway Specifications",
        "department": "Engineering",
        "raw_text": "All internal endpoints communicate over mTLS. Rate limiting is set to 100 req/sec.",
        "permitted_principals": ["engineering_lead"]
    }, headers=auth_headers)
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    # Fetch detail
    detail = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
    assert detail.status_code == 200
    data = detail.json()
    assert data["chunks_count"] >= 1
    assert "mTLS" in data["raw_text"]
