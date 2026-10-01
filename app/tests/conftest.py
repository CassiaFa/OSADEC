"""
Shared pytest fixtures for the OSADEC `/api` test suite (Phase 6 of the
redesign, see docs/redesign/ROADMAP.md).

Must be run from inside the `osadec` container: `Database.__HOST` is the
literal string `"db"` (app/src/utils/db_tools.py), which only resolves on the
docker-compose network. See docs/testing.md for the exact invocation.

All fixtures here create their own isolated project/file/detections
(`pytest_fixture_*`, cleaned up after the session) rather than touching the
pre-existing dataset (19-20 files / 5200+ detections) or the `test_toto`
project / id_file=32 fixture other agents use for manual/visual QA - this
suite only ever *reads* record 32 (for the one test that needs real audio
bytes on disk), never writes to it.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

# app.py (and everything it imports with bare `from src...` / relative `tmp/`
# paths) assumes it runs from the app/ directory (== /osadec in the
# container, the Dockerfile's WORKDIR) - same as `python app.py` / `CMD
# ["python", "app.py"]`. Make that true regardless of where pytest was
# invoked from.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)
os.chdir(APP_ROOT)

import app as app_module  # noqa: E402
from src.utils.db_tools import Database  # noqa: E402


FIXTURE_PROJECT_NAME = "pytest_fixture_project"
FIXTURE_FILE_NAME = "pytest_fixture_record.wav"
FIXTURE_FILE_DATE = datetime(2021, 6, 1, 12, 0, 0)
FIXTURE_FILE_DURATION = 600
FIXTURE_FILE_FS = 1000
# Deliberately not a real path: nothing in this suite needs to read actual
# audio bytes from this fixture file (the spectrogram "happy path" test uses
# the pre-existing record id 32 / test_20150318_110000.wav instead - the only
# record in this environment that has real audio on disk, see
# docs/testing.md). This fixture only exercises DB-only endpoints (detections
# listing/CSV, review status, project stats/listing), plus the spectrogram
# endpoint's "record exists but its audio file is missing" 404 branch.
FIXTURE_FILE_PATH = "/nonexistent/pytest-fixture"

# (offset_start_seconds, offset_stop_seconds, freq_min, freq_max, confidence, id_species)
FIXTURE_DETECTIONS = [
    (10, 12, 50.0, 60.0, 0.9, 6),      # Blue whale
    (100, 105, 20.0, 40.0, 0.75, 7),   # Fin whale
]

REAL_RECORD_ID = 32  # pre-existing fixture with real audio on disk; read-only in this suite.


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture()
def logged_in_session(client):
    """
    Fakes a signed-in session (see `flask.session["user"]` in app.py /
    src/api/records.py) without needing a real row in `users` -
    `PATCH /api/detections/<id>` only reads `session["user"]["id"]` to stamp
    `reviewed_by`, it does not validate it against the `users` table.
    """
    with client.session_transaction() as sess:
        sess["user"] = {"id": 999001, "username": "pytest"}
    return client


@pytest.fixture(scope="session")
def fixture_record():
    """
    Creates an isolated project + file + detections for the duration of the
    test session, and deletes them again afterwards.
    """
    Database.open_connexion()
    try:
        if not Database.get_projects(name=FIXTURE_PROJECT_NAME):
            Database.add_project(FIXTURE_PROJECT_NAME, 100, 36.0, -121.0)
        id_project = Database.get_projects(name=FIXTURE_PROJECT_NAME)["id_project"]

        if not Database.get_files(name=FIXTURE_FILE_NAME):
            Database.add_file(
                FIXTURE_FILE_NAME, FIXTURE_FILE_DATE, FIXTURE_FILE_DURATION,
                FIXTURE_FILE_FS, FIXTURE_FILE_PATH, id_project,
            )
        id_file = Database.get_files(name=FIXTURE_FILE_NAME)["id_file"]

        for start_off, stop_off, fmin, fmax, confidence, id_species in FIXTURE_DETECTIONS:
            start = FIXTURE_FILE_DATE + timedelta(seconds=start_off)
            stop = FIXTURE_FILE_DATE + timedelta(seconds=stop_off)
            Database.add_detection(start, stop, confidence, id_species, id_file, fmin, fmax)

        rows = Database.get_detections(id_file=id_file)
        if isinstance(rows, dict):
            rows = [rows]
        detection_ids = sorted(r["id_detection"] for r in rows)
    finally:
        Database.close_connexion()

    yield {
        "id_project": id_project,
        "id_file": id_file,
        "detection_ids": detection_ids,
        "offsets": FIXTURE_DETECTIONS,
        "file_date": FIXTURE_FILE_DATE,
    }

    Database.open_connexion()
    try:
        cursor = Database._Database__cursor
        connexion = Database._Database__bdd
        cursor.execute("DELETE FROM DETECTIONS WHERE id_file=%s", (id_file,))
        cursor.execute("DELETE FROM FILES WHERE id_file=%s", (id_file,))
        cursor.execute("DELETE FROM PROJECTS WHERE id_project=%s", (id_project,))
        connexion.commit()
    finally:
        Database.close_connexion()
