def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_unknown_api_route_is_json_404(client):
    resp = client.get("/api/this-route-does-not-exist")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_found"
