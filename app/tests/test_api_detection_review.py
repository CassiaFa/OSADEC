"""
PATCH /api/detections/<id> (Phase 3 of the redesign): review status
transitions (pending -> confirmed -> rejected -> pending), auth requirement,
and `reviewed_by`/`reviewed_at` bookkeeping.
"""


def test_patch_requires_session(client, fixture_record):
    id_detection = fixture_record["detection_ids"][0]
    resp = client.patch(f"/api/detections/{id_detection}", json={"review_status": "confirmed"})
    assert resp.status_code == 401


def test_patch_rejects_invalid_status(client, logged_in_session, fixture_record):
    id_detection = fixture_record["detection_ids"][0]
    resp = logged_in_session.patch(f"/api/detections/{id_detection}", json={"review_status": "bogus"})
    assert resp.status_code == 400


def test_patch_unknown_detection_is_404(client, logged_in_session):
    resp = logged_in_session.patch("/api/detections/999999999", json={"review_status": "confirmed"})
    assert resp.status_code == 404


def test_patch_full_review_cycle(client, logged_in_session, fixture_record):
    id_detection = fixture_record["detection_ids"][-1]

    resp = logged_in_session.patch(f"/api/detections/{id_detection}", json={"review_status": "confirmed"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["review_status"] == "confirmed"
    assert body["reviewed_by"] == 999001
    assert body["reviewed_at"] is not None

    resp = logged_in_session.patch(f"/api/detections/{id_detection}", json={"review_status": "rejected"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["review_status"] == "rejected"
    assert body["reviewed_by"] == 999001
    assert body["reviewed_at"] is not None

    resp = logged_in_session.patch(f"/api/detections/{id_detection}", json={"review_status": "pending"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["review_status"] == "pending"
    # update_detection_status() (db_tools.py) clears reviewed_at (but keeps
    # reviewed_by) once a detection goes back to 'pending'.
    assert body["reviewed_at"] is None
    assert body["reviewed_by"] == 999001
