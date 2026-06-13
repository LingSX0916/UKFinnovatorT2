"""API integration — endpoint contracts + the end-to-end RED flow, all offline
(CH fixtures + sample sanctions list, no key, no Supabase). Also asserts no secret
ever leaks into a response."""
import pytest


@pytest.fixture(scope="module")
def client():
    from backend.api import app
    from backend.kyb import screening
    screening.get_index(force=True)  # bind to the committed sample list
    return app.test_client()


def test_health(client):
    r = client.get("/api/health").get_json()
    assert r["status"] == "ok"
    assert r["companies_house"] == "fixtures"
    assert r["sanctions_index"]["designations"] >= 8
    assert r["persistence"] is False


def test_search(client):
    items = client.get("/api/company/search?q=northwind").get_json()["items"]
    assert any(i["company_number"] == "SC900001" for i in items)


def test_search_requires_query(client):
    assert client.get("/api/company/search").status_code == 400


def test_dossier(client):
    d = client.get("/api/company/SC900001").get_json()
    assert d["profile"]["name"]
    assert len(d["ownership_graph"]["nodes"]) >= 2  # resolves indirect ownership


def test_unknown_company_404(client):
    assert client.get("/api/company/ZZ999999").status_code == 404


def test_invalid_company_number_rejected(client):
    # SSRF / path-traversal guard: a malformed number is 400, never reaches a sink
    assert client.get("/api/company/..%5C..%5Csecret").status_code == 400
    assert client.get("/api/company/abc").status_code == 400  # too short
    assert client.post("/api/company/foo$bar/screen", json={}).status_code == 400


def test_screen_red_with_evidence(client):
    r = client.post("/api/company/SC900001/screen",
                    json={"run_by": "tester", "as_of": "2026-06-13"}).get_json()
    assert r["overall_verdict"] == "RED"
    assert any(m["matched_designation_id"] == "RUS0001" for m in r["matches"])
    # no verdict without evidence
    for m in r["matches"]:
        assert m["evidence"] and m["matched_fields"]
    # ownership & control factor fired and cites a provision
    oac = [f for f in r["risk_assessment"]["factors"]
           if f["code"] == "OWNERSHIP_AND_CONTROL" and f["triggered"]]
    assert oac and oac[0]["provision"]


def test_screen_green(client):
    r = client.post("/api/company/00000002/screen", json={}).get_json()
    assert r["overall_verdict"] == "GREEN"
    assert r["matches"] == []


def test_match_decision(client):
    r = client.post("/api/company/SC900003/screen", json={}).get_json()
    mid = r["matches"][0]["id"]
    d = client.post(f"/api/screening/match/{mid}/decision",
                    json={"decision": "dismissed", "note": "namesake, different DOB"}).get_json()
    assert d["decision"] == "dismissed"


def test_export_json_and_pdf(client):
    assert client.get("/api/company/SC900001/export?format=json").status_code == 200
    pdf = client.get("/api/company/SC900001/export?format=pdf")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"


def test_no_secret_leaks_in_response(client):
    body = client.post("/api/company/SC900001/screen", json={}).get_data(as_text=True)
    for needle in ("service_role", "SERVICE_ROLE", "sb_secret", "COMPANIES_HOUSE_API_KEY"):
        assert needle not in body
