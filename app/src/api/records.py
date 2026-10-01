"""
Phase 3 of the redesign (see docs/redesign/ROADMAP.md): on-demand spectrogram
images, detection listing/export and detection review, all served as JSON/PNG
under the `/api` blueprint defined in `app/src/api/__init__.py`.

Routes defined here:
    GET   /api/records/<id_file>/spectrogram
    GET   /api/records/<id_file>/detections
    GET   /api/records/<id_file>/detections.csv
    PATCH /api/detections/<id_detection>

Design notes
------------
Spectrogram images are expensive to compute (matplotlib + STFT on CPU, same
machine as the Faster R-CNN model). They are rendered on demand into a
dedicated cache directory (`CACHE_DIR`, inside the `tmp/` volume already
mounted in docker-compose.yml) using a unique filename derived from the
record id and the requested window (start/end/fmin/fmax). This is intentionally
*not* the shared `./tmp/tmp.png` used by `compute_pipline.pipeline()` for
inference, which is written/removed on every analysis run and was never meant
to be served to a browser.

Alongside each cached PNG, a small JSON sidecar (same basename, `.json`
extension) stores the axis geometry returned by `Spectrogram.axis_bounds()`
(see pixlabel.py). This avoids re-deriving the geometry analytically on a
cache hit (which would duplicate - and risk drifting from - the STFT math),
at the cost of one extra small file per cache entry.

The chosen response shape for the spectrogram endpoint is a PNG body with the
axis geometry in `X-Axis-*` response headers (rather than a JSON wrapper
pointing at a second image URL). This keeps the contract to a single request:
a `fetch()` on the client gets both the image bytes and the headers it needs
to position detection boxes in one round trip, and the same URL can still be
used directly as an `<img src>` for simple display without reading headers at
all.
"""

import hashlib
import json
import os

from flask import Response, abort, request, send_file, session

from . import api_bp
from ..utils.compute_pipline import compute_spectro
from ..utils.db_tools import Database

# Dedicated cache directory for on-demand spectrogram renders. Lives inside the
# `tmp/` volume already mounted by docker-compose (./app/tmp -> /osadec/tmp),
# but in its own subfolder so it never collides with the shared `tmp/tmp.png`
# used (and deleted) by the inference pipeline.
CACHE_DIR = os.path.join("tmp", "spectrogram_cache")

# Matches the historical rendering in pixlabel.py / compute_pipline.py.
DEFAULT_FREQ_MIN = 15.0
DEFAULT_FREQ_MAX = 200.0
DEFAULT_WINDOW_SECONDS = 300


def _get_file_or_404(id_file):
    Database.open_connexion()
    try:
        file_row = Database.get_files(id_file=id_file)
    finally:
        Database.close_connexion()

    if not file_row:
        abort(404, description=f"Record {id_file} not found.")
    return file_row


def _species_name_map():
    Database.open_connexion()
    try:
        categories = Database.get_categories()
    finally:
        Database.close_connexion()

    if isinstance(categories, dict):
        categories = [categories]
    return {c["id_species"]: c["english_name"] for c in categories}


def _enriched_detections(id_file, file_row):
    """
    Returns the detections of `id_file` as plain dicts matching the Phase 3
    contract: `{id, t_start, t_end, f_min, f_max, confidence, species,
    review_status}`, with times converted from absolute datetimes
    (`DETECTIONS.start`/`stop`) to seconds relative to `FILES.date`.
    """

    Database.open_connexion()
    try:
        rows = Database.get_detections(id_file=id_file)
    finally:
        Database.close_connexion()

    if isinstance(rows, dict):
        rows = [rows]

    species_map = _species_name_map()
    file_start = file_row["date"]

    detections = []
    for row in rows:
        detections.append({
            "id": row["id_detection"],
            "t_start": (row["start"] - file_start).total_seconds(),
            "t_end": (row["stop"] - file_start).total_seconds(),
            "f_min": row["freq_min"],
            "f_max": row["freq_max"],
            "confidence": row["confidence"],
            "species": species_map.get(row["id_species"]),
            "review_status": row["review_status"],
        })

    return detections


def _cache_key(id_file, start, end, fmin, fmax):
    raw = f"{id_file}:{start:.3f}:{end:.3f}:{fmin:.2f}:{fmax:.2f}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]
    return f"record{id_file}_{digest}"


@api_bp.route("/records/<int:id_file>/spectrogram", methods=["GET"])
def record_spectrogram(id_file):
    """
    Renders (or serves from cache) the spectrogram PNG for `id_file` over the
    requested time window / frequency band, matching the STFT parameters used
    by the inference pipeline (nfft=4096, win_size=2000, overlap 90%, Hamming
    window, 20Hz Butterworth high-pass, resampled to 2000Hz).

    Query params (all optional):
        start, end: seconds relative to the start of the file. Default: the
            first DEFAULT_WINDOW_SECONDS (or the full file if shorter).
        fmin, fmax: Hz. Default: 15-200Hz (the historical display band).

    Response: image/png, with the rendered axis geometry in headers so the
    client can reposition detection boxes without matplotlib:
        X-Axis-Time-Start, X-Axis-Time-End (seconds, actual rendered x-limits,
            which may be a hair narrower than the requested start/end - see
            Spectrogram.axis_bounds()),
        X-Axis-Freq-Min, X-Axis-Freq-Max (Hz),
        X-Axis-Pixel-X, X-Axis-Pixel-Y, X-Axis-Pixel-Width, X-Axis-Pixel-Height:
            bounding box (top-left origin, image pixel coordinates) of the
            plotted data area within the PNG,
        X-Axis-Image-Width, X-Axis-Image-Height: full PNG dimensions.
    """

    file_row = _get_file_or_404(id_file)
    duration = file_row["duration"]

    start = request.args.get("start", default=0.0, type=float)
    default_end = float(min(duration, DEFAULT_WINDOW_SECONDS))
    end = request.args.get("end", default=default_end, type=float)
    fmin = request.args.get("fmin", default=DEFAULT_FREQ_MIN, type=float)
    fmax = request.args.get("fmax", default=DEFAULT_FREQ_MAX, type=float)

    if start is None or end is None or start < 0 or end <= start:
        abort(400, description="`start` must be >= 0 and `end` must be greater than `start`.")
    if end > duration:
        end = float(duration)
    if fmin is None or fmax is None or fmin < 0 or fmax <= fmin:
        abort(400, description="`fmin` must be >= 0 and `fmax` must be greater than `fmin`.")

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_key = _cache_key(id_file, start, end, fmin, fmax)
    img_path = os.path.join(CACHE_DIR, f"{cache_key}.png")
    bounds_path = os.path.join(CACHE_DIR, f"{cache_key}.json")

    if os.path.exists(img_path) and os.path.exists(bounds_path):
        with open(bounds_path, "r") as fh:
            bounds = json.load(fh)
    else:
        filepath = os.path.join(file_row["path"], file_row["name"])
        if not os.path.exists(filepath):
            abort(404, description=f"Audio file for record {id_file} not found on disk.")

        spectro = compute_spectro(
            filepath, start, end, file_row["fs"], f"{cache_key}.png", CACHE_DIR,
            freq_min=fmin, freq_max=fmax,
        )
        try:
            bounds = spectro.axis_bounds()
        finally:
            spectro.close()
            del spectro

        # `Spectrogram` only ever sees the loaded excerpt, so its axis_bounds()
        # time values are relative to the start of *that excerpt* (i.e. to
        # `start`), not to the start of the file. The detections endpoint
        # returns file-relative seconds (see `_enriched_detections`), so these
        # headers must use the same reference frame for the client to be able
        # to line up detection boxes with the image.
        bounds["time_start"] += start
        bounds["time_end"] += start

        with open(bounds_path, "w") as fh:
            json.dump(bounds, fh)

    response = send_file(img_path, mimetype="image/png")
    response.headers["X-Axis-Time-Start"] = str(bounds["time_start"])
    response.headers["X-Axis-Time-End"] = str(bounds["time_end"])
    response.headers["X-Axis-Freq-Min"] = str(bounds["freq_min"])
    response.headers["X-Axis-Freq-Max"] = str(bounds["freq_max"])
    response.headers["X-Axis-Pixel-X"] = str(bounds["pixel_x"])
    response.headers["X-Axis-Pixel-Y"] = str(bounds["pixel_y"])
    response.headers["X-Axis-Pixel-Width"] = str(bounds["pixel_width"])
    response.headers["X-Axis-Pixel-Height"] = str(bounds["pixel_height"])
    response.headers["X-Axis-Image-Width"] = str(bounds["image_width"])
    response.headers["X-Axis-Image-Height"] = str(bounds["image_height"])
    # Allow the viewer's JS to read the custom headers on cross-origin fetches
    # too (harmless same-origin default here, but one less surprise later).
    response.headers["Access-Control-Expose-Headers"] = (
        "X-Axis-Time-Start, X-Axis-Time-End, X-Axis-Freq-Min, X-Axis-Freq-Max, "
        "X-Axis-Pixel-X, X-Axis-Pixel-Y, X-Axis-Pixel-Width, X-Axis-Pixel-Height, "
        "X-Axis-Image-Width, X-Axis-Image-Height"
    )
    return response


@api_bp.route("/records/<int:id_file>/detections", methods=["GET"])
def record_detections(id_file):
    """
    Returns the detections of `id_file` as
    `[{id, t_start, t_end, f_min, f_max, confidence, species, review_status}]`,
    with times in seconds relative to the start of the file.
    """
    file_row = _get_file_or_404(id_file)
    return {"detections": _enriched_detections(id_file, file_row)}


@api_bp.route("/records/<int:id_file>/detections.csv", methods=["GET"])
def record_detections_csv(id_file):
    """
    Enriched CSV export of the detections of `id_file`: `id, t_start, t_end,
    f_min, f_max, confidence, species, review_status`. This is a separate,
    richer export than the pre-existing `/account/csv/<id>/<file>` route
    (which only exports `start, end, confidence` as absolute datetimes, and is
    left untouched for backward compatibility); this one is consistent with
    the `/api/records/<id>/detections` JSON contract (relative seconds,
    species name, review status).
    """
    file_row = _get_file_or_404(id_file)
    detections = _enriched_detections(id_file, file_row)

    columns = ["id", "t_start", "t_end", "f_min", "f_max", "confidence", "species", "review_status"]
    lines = [",".join(columns)]
    for d in detections:
        lines.append(",".join(
            "" if d[c] is None else str(d[c])
            for c in columns
        ))
    csv_body = "\n".join(lines) + "\n"

    response = Response(csv_body, mimetype="text/csv")
    response.headers["Content-Disposition"] = (
        f"attachment; filename={file_row['name'].rsplit('.', 1)[0]}_detections.csv"
    )
    return response


@api_bp.route("/detections/<int:id_detection>", methods=["PATCH"])
def update_detection(id_detection):
    """
    Updates the review status of a single detection. Body: `{"review_status":
    "confirmed"|"rejected"|"pending"}`. Requires an active session (same
    requirement as the rest of `/account`); there is no per-user ownership
    check (no project/user cloisonnement in this project yet), but
    `reviewed_by` is set from the session user when available.
    """
    if not session.get("user"):
        abort(401, description="Authentication required.")

    body = request.get_json(silent=True) or {}
    review_status = body.get("review_status")
    if review_status not in ("pending", "confirmed", "rejected"):
        abort(400, description="`review_status` must be one of 'pending', 'confirmed', 'rejected'.")

    Database.open_connexion()
    try:
        detection = Database.get_detection(id_detection)
        if not detection:
            abort(404, description=f"Detection {id_detection} not found.")

        reviewed_by = session["user"].get("id")
        Database.update_detection_status(id_detection, review_status, reviewed_by=reviewed_by)
        updated = Database.get_detection(id_detection)
    finally:
        Database.close_connexion()

    return {
        "id": updated["id_detection"],
        "review_status": updated["review_status"],
        "reviewed_by": updated["reviewed_by"],
        "reviewed_at": updated["reviewed_at"].isoformat() if updated["reviewed_at"] else None,
    }
