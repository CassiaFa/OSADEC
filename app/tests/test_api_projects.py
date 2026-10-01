"""
GET /api/projects, /api/projects/<id>/stats, /api/projects/<id>/records and
/api/records (Phase 2 of the redesign): project picker, dashboard stats and
the paginated/filtered explorer listing.
"""


def test_list_projects_includes_fixture(client, fixture_record):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    projects = {p["name"]: p for p in resp.get_json()["projects"]}
    assert "pytest_fixture_project" in projects
    assert projects["pytest_fixture_project"]["file_count"] == 1


def test_project_stats(client, fixture_record):
    resp = client.get(f"/api/projects/{fixture_record['id_project']}/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["records"] == 1
    assert data["detections"] == len(fixture_record["offsets"])
    assert data["pending_detections"] == len(fixture_record["offsets"])
    assert {s["name"] for s in data["species"]} == {"Blue whale", "Fin whale"}


def test_project_stats_unknown_project_is_404(client):
    resp = client.get("/api/projects/999999/stats")
    assert resp.status_code == 404


def test_project_records_listing(client, fixture_record):
    resp = client.get(f"/api/projects/{fixture_record['id_project']}/records")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["records"][0]["id"] == fixture_record["id_file"]
    assert data["records"][0]["detections"] == len(fixture_record["offsets"])
    assert data["records"][0]["status"] == "pending"


def test_all_records_listing_search_finds_fixture(client, fixture_record):
    resp = client.get("/api/records", query_string={"q": "pytest_fixture_record"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["records"][0]["id"] == fixture_record["id_file"]


def test_records_listing_rejects_bad_sort(client):
    resp = client.get("/api/records", query_string={"sort": "bogus"})
    assert resp.status_code == 400


def test_records_listing_rejects_bad_status(client):
    resp = client.get("/api/records", query_string={"status": "bogus"})
    assert resp.status_code == 400


def test_list_species(client):
    resp = client.get("/api/species")
    assert resp.status_code == 200
    species = resp.get_json()["species"]
    names = {s["name"] for s in species}
    assert {"Blue whale", "Fin whale"}.issubset(names)
