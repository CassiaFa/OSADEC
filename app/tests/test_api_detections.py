"""
GET /api/records/<id>/detections and /detections.csv (Phase 3 of the
redesign): JSON shape, absolute-datetime -> file-relative-seconds conversion,
and the enriched CSV export.
"""

import pytest


def test_record_detections_relative_seconds(client, fixture_record):
    resp = client.get(f"/api/records/{fixture_record['id_file']}/detections")
    assert resp.status_code == 200

    data = resp.get_json()["detections"]
    assert len(data) == len(fixture_record["offsets"])

    by_bounds = {(d["t_start"], d["t_end"]): d for d in data}
    for start_off, stop_off, fmin, fmax, confidence, _id_species in fixture_record["offsets"]:
        key = (float(start_off), float(stop_off))
        assert key in by_bounds, f"missing detection at offsets {key}, got {sorted(by_bounds)}"
        det = by_bounds[key]
        assert det["f_min"] == pytest.approx(fmin)
        assert det["f_max"] == pytest.approx(fmax)
        assert det["confidence"] == pytest.approx(confidence)
        assert det["review_status"] == "pending"
        assert det["species"] in ("Blue whale", "Fin whale")
        assert isinstance(det["id"], int)


def test_record_detections_unknown_record_is_404(client):
    resp = client.get("/api/records/999999/detections")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not_found"


def test_record_detections_csv_shape(client, fixture_record):
    resp = client.get(f"/api/records/{fixture_record['id_file']}/detections.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers.get("Content-Disposition", "")

    lines = resp.get_data(as_text=True).strip().splitlines()
    assert lines[0] == "id,t_start,t_end,f_min,f_max,confidence,species,review_status"
    assert len(lines) == 1 + len(fixture_record["offsets"])
