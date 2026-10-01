"""
GET /api/records/<id>/spectrogram (Phase 3 of the redesign): on-demand PNG
rendering + the `X-Axis-*` geometry headers, and its error cases.

The happy-path test needs an actual `.wav` on disk: `app/bucket` only
contains one in this environment, `test_20150318_110000.wav` / id_file=32
(the other agents' shared manual-QA fixture, see docs/testing.md). This suite
only ever issues GET requests against it, never mutates it.
"""

import pytest

# Must match conftest.REAL_RECORD_ID (kept as a plain literal here rather than
# imported, so this file has no package-relative import dependency on
# conftest.py - see docs/testing.md for how the suite is invoked).
REAL_RECORD_ID = 32

AXIS_HEADERS = (
    "X-Axis-Time-Start", "X-Axis-Time-End", "X-Axis-Freq-Min", "X-Axis-Freq-Max",
    "X-Axis-Pixel-X", "X-Axis-Pixel-Y", "X-Axis-Pixel-Width", "X-Axis-Pixel-Height",
    "X-Axis-Image-Width", "X-Axis-Image-Height",
)


def test_spectrogram_happy_path(client):
    resp = client.get(f"/api/records/{REAL_RECORD_ID}/spectrogram?start=0&end=5&fmin=15&fmax=200")
    if resp.status_code == 404:
        pytest.skip(f"record {REAL_RECORD_ID} or its audio file is not present in this environment")

    assert resp.status_code == 200
    assert resp.mimetype == "image/png"
    for header in AXIS_HEADERS:
        assert header in resp.headers, f"missing header {header}"

    assert float(resp.headers["X-Axis-Freq-Min"]) == pytest.approx(15.0)
    assert float(resp.headers["X-Axis-Freq-Max"]) == pytest.approx(200.0)
    assert float(resp.headers["X-Axis-Time-End"]) > float(resp.headers["X-Axis-Time-Start"]) >= 0


def test_spectrogram_invalid_time_range_is_400(client):
    resp = client.get(f"/api/records/{REAL_RECORD_ID}/spectrogram?start=5&end=1")
    assert resp.status_code == 400


def test_spectrogram_invalid_frequency_range_is_400(client):
    resp = client.get(f"/api/records/{REAL_RECORD_ID}/spectrogram?fmin=200&fmax=15")
    assert resp.status_code == 400


def test_spectrogram_unknown_record_is_404(client):
    resp = client.get("/api/records/999999/spectrogram")
    assert resp.status_code == 404


def test_spectrogram_missing_audio_file_is_404(client, fixture_record):
    # fixture_record's FILES row points at a path that doesn't exist on disk
    # (see conftest.FIXTURE_FILE_PATH) - exercises the "record exists but its
    # audio is missing" 404 branch, distinct from "record id doesn't exist".
    resp = client.get(f"/api/records/{fixture_record['id_file']}/spectrogram")
    assert resp.status_code == 404
