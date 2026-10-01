"""
Phase 2 of the redesign (see docs/redesign/ROADMAP.md): project-scoped stats and
a filtered/paginated record listing, consumed client-side (fetch) by the new
dashboard (`/dashboard`) and explorer (`/files`) templates. No HTML is rendered
here; `app.py` only renders the page shells, all data comes from this module.

Routes defined here:
    GET /api/projects                       - project picker (id, name, file_count)
    GET /api/projects/<id>/stats             - dashboard summary cards
    GET /api/projects/<id>/records           - explorer listing (search/filter/sort/paginate)
    GET /api/records/<id>/thumbnail          - low-res dashboard/explorer spectrogram thumbnail

Design notes
------------
There is no per-user project ownership yet (see "Décisions à trancher" /
PROJECTS.id_user in the roadmap), so every signed-in user sees every project -
consistent with the rest of the app today.

`Database.get_files` / `Database.get_projects` only support filtering by plain
FILES/PROJECTS columns (name, date range, id_project - extended in this phase
for `id_project`/`limit`/`offset`). Species and review-status filters need
DETECTIONS joined to FILES, which the dataset is far too small (19 files, ~5.2k
detections total) to justify pushing into SQL for this phase: detections are
fetched once per request and grouped by `id_file` in Python
(`_detections_by_file`), then search/species/status filtering, sorting and
pagination for `/records` all happen in Python on that combined view. If the
dataset grows a lot this should move to a SQL join with `GROUP BY`, but that is
not needed today and would duplicate the status logic in two places.

Record / project review status (`new` / `pending` / `reviewed`) is derived here
from the per-detection `review_status` column (no detections at all -> `new`;
at least one `pending` detection -> `pending`, displayed as "In review" by the
client; otherwise -> `reviewed`). This is the same 3-state model the Phase 4
viewer will need for its own per-record status - defined once here so it is not
reinvented when the viewer lands.
"""

import os

from flask import abort, request, send_file

from . import api_bp
from ..utils.compute_pipline import generate_thumbnail, thumbnail_path
from ..utils.db_tools import Database


def _as_list(rows):
    """Database methods collapse a 1-row result to a dict; normalize to a list."""
    if rows is None:
        return []
    if isinstance(rows, dict):
        return [rows]
    return rows


def _get_project_or_404(id_project):
    Database.open_connexion()
    try:
        project = Database.get_projects(id_project=id_project)
    finally:
        Database.close_connexion()

    if not project:
        abort(404, description=f"Project {id_project} not found.")
    return project


def _species_name_map():
    Database.open_connexion()
    try:
        categories = Database.get_categories()
    finally:
        Database.close_connexion()

    return {c["id_species"]: c["english_name"] for c in _as_list(categories)}


def _detections_by_file(id_files):
    """
    Returns `{id_file: [detection_row, ...]}` for the given file ids, fetched in
    a single query (`Database.get_detections()` with no filter returns every
    detection with its `id_file`) and grouped in Python - see module docstring.
    """
    id_files = set(id_files)
    Database.open_connexion()
    try:
        rows = Database.get_detections()
    finally:
        Database.close_connexion()

    by_file = {}
    for row in _as_list(rows):
        if row["id_file"] in id_files:
            by_file.setdefault(row["id_file"], []).append(row)
    return by_file


def _get_file_or_404(id_file):
    Database.open_connexion()
    try:
        file_row = Database.get_files(id_file=id_file)
    finally:
        Database.close_connexion()

    if not file_row:
        abort(404, description=f"Record {id_file} not found.")
    return file_row


def _has_thumbnail(id_file, file_row):
    """
    Whether `GET /api/records/<id_file>/thumbnail` can/will return a real PNG:
    either already cached (`bucket/spectrograms/<id_file>.png`), or the
    record's `.wav` is actually present on disk so the route can render one
    lazily on first request (see `compute_pipline.generate_thumbnail`).

    False for most of the demo dataset today (19 files, only one - `id_file
    32`, uploaded after the rest - has a real `.wav` on disk in this
    environment, see CLAUDE.md); the client should fall back to the CSS
    gradient placeholder (`.record-thumb--empty` in `app/static/css/app.css`)
    whenever this is `False`.
    """
    if os.path.exists(thumbnail_path(id_file)):
        return True
    filepath = os.path.join(file_row["path"], file_row["name"])
    return os.path.exists(filepath)


def _record_status(detections):
    """Derive the 3-state record status from its detections' review_status."""
    if not detections:
        return "new"
    if any(d["review_status"] == "pending" for d in detections):
        return "pending"
    return "reviewed"


@api_bp.route("/projects", methods=["GET"])
def list_projects():
    """Lightweight project list for the top-bar project switcher."""
    Database.open_connexion()
    try:
        projects = _as_list(Database.get_projects())
        files = _as_list(Database.get_files())
    finally:
        Database.close_connexion()

    file_counts = {}
    for f in files:
        file_counts[f["id_project"]] = file_counts.get(f["id_project"], 0) + 1

    return {
        "projects": [
            {
                "id": p["id_project"],
                "name": p["name"],
                "file_count": file_counts.get(p["id_project"], 0),
            }
            for p in sorted(projects, key=lambda p: p["name"])
        ]
    }


@api_bp.route("/projects/<int:id_project>/stats", methods=["GET"])
def project_stats(id_project):
    """
    Dashboard summary for `id_project`: record/detection counts, total audio
    duration, species breakdown and the count of detections still pending
    review.
    """
    project = _get_project_or_404(id_project)

    Database.open_connexion()
    try:
        files = _as_list(Database.get_files(id_project=id_project))
    finally:
        Database.close_connexion()

    id_files = [f["id_file"] for f in files]
    detections_by_file = _detections_by_file(id_files) if id_files else {}
    species_map = _species_name_map()

    total_duration = sum((f["duration"] or 0) for f in files)
    species_counts = {}
    nb_detections = 0
    nb_pending = 0
    for dets in detections_by_file.values():
        for d in dets:
            nb_detections += 1
            if d["review_status"] == "pending":
                nb_pending += 1
            species_counts[d["id_species"]] = species_counts.get(d["id_species"], 0) + 1

    species = [
        {"id": id_species, "name": species_map.get(id_species, f"Species {id_species}"), "count": count}
        for id_species, count in sorted(species_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]

    return {
        "project": {
            "id": project["id_project"],
            "name": project["name"],
            "depth": project["depth"],
            "latitude": project["latitude"],
            "longitude": project["longitude"],
        },
        "records": len(files),
        "detections": nb_detections,
        "audio_hours": round(total_duration / 3600, 1),
        "species_count": len(species_counts),
        "species": species,
        "pending_detections": nb_pending,
    }


def _parse_list_args():
    """Shared query-param parsing/validation for both record-listing routes."""
    args = {
        "q": (request.args.get("q") or "").strip().lower(),
        "species_filter": request.args.get("species", type=int),
        "status_filter": request.args.get("status"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
        "sort": request.args.get("sort", default="date"),
        "direction": request.args.get("dir", default="desc"),
        "page": max(1, request.args.get("page", default=1, type=int) or 1),
    }
    page_size = request.args.get("page_size", default=10, type=int) or 10
    args["page_size"] = max(1, min(page_size, 100))

    if args["status_filter"] not in (None, "new", "pending", "reviewed"):
        abort(400, description="`status` must be one of 'new', 'pending', 'reviewed'.")
    if args["sort"] not in ("name", "date", "detections", "duration"):
        abort(400, description="`sort` must be one of 'name', 'date', 'detections', 'duration'.")
    return args


def _build_records(files, project_name_by_id):
    """
    Turns FILES rows into the explorer's record shape (species/status resolved
    from DETECTIONS), unfiltered/unsorted/unpaginated - shared by the
    single-project and all-projects listing routes below. `species_ids` is
    kept on each record for filtering by `_filter_sort_paginate` and stripped
    before the response is returned.
    """
    id_files = [f["id_file"] for f in files]
    detections_by_file = _detections_by_file(id_files) if id_files else {}
    species_map = _species_name_map()

    records = []
    for f in files:
        dets = detections_by_file.get(f["id_file"], [])
        species_ids = sorted({d["id_species"] for d in dets})
        pending = sum(1 for d in dets if d["review_status"] == "pending")
        records.append({
            "id": f["id_file"],
            "name": f["name"],
            "project_name": project_name_by_id.get(f["id_project"], "—"),
            "date": f["date"].isoformat() if f["date"] else None,
            "duration_seconds": f["duration"],
            "detections": len(dets),
            "pending_detections": pending,
            "species": [species_map.get(i, f"Species {i}") for i in species_ids],
            "species_ids": species_ids,
            "status": _record_status(dets),
            "has_thumbnail": _has_thumbnail(f["id_file"], f),
        })
    return records


def _filter_sort_paginate(records, args):
    filtered = []
    for r in records:
        if args["q"] and args["q"] not in r["name"].lower():
            continue
        if args["species_filter"] is not None and args["species_filter"] not in r["species_ids"]:
            continue
        if args["status_filter"] and r["status"] != args["status_filter"]:
            continue
        filtered.append(r)

    sort_key = {
        "name": lambda r: r["name"],
        "date": lambda r: r["date"] or "",
        "detections": lambda r: r["detections"],
        "duration": lambda r: r["duration_seconds"] or 0,
    }[args["sort"]]
    filtered.sort(key=sort_key, reverse=(args["direction"] != "asc"))

    total = len(filtered)
    page_size = args["page_size"]
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(args["page"], pages)
    start = (page - 1) * page_size
    page_records = [{k: v for k, v in r.items() if k != "species_ids"} for r in filtered[start:start + page_size]]
    return page_records, total, page, pages


@api_bp.route("/projects/<int:id_project>/records", methods=["GET"])
def project_records(id_project):
    """
    Filtered/sorted/paginated record listing for the explorer (`/files`),
    scoped to a single project. See `all_records` below for the "All
    projects" variant used when the explorer's project switcher is cleared.

    Query params (all optional): see `_parse_list_args`.
    """
    project = _get_project_or_404(id_project)
    args = _parse_list_args()

    Database.open_connexion()
    try:
        files = _as_list(Database.get_files(
            id_project=id_project,
            time_min=args["date_from"],
            time_max=args["date_to"],
        ))
    finally:
        Database.close_connexion()

    records = _build_records(files, {id_project: project["name"]})
    page_records, total, page, pages = _filter_sort_paginate(records, args)

    return {
        "project": {"id": project["id_project"], "name": project["name"]},
        "records": page_records,
        "total": total,
        "page": page,
        "page_size": args["page_size"],
        "pages": pages,
    }


@api_bp.route("/records", methods=["GET"])
def all_records():
    """
    Same as `project_records`, but across every project at once - used by the
    explorer when its project switcher is set to "All projects" (no
    `id_project` in the URL). Each record carries its own `project_name`.
    """
    args = _parse_list_args()

    Database.open_connexion()
    try:
        files = _as_list(Database.get_files(time_min=args["date_from"], time_max=args["date_to"]))
        projects = _as_list(Database.get_projects())
    finally:
        Database.close_connexion()

    project_name_by_id = {p["id_project"]: p["name"] for p in projects}
    records = _build_records(files, project_name_by_id)
    page_records, total, page, pages = _filter_sort_paginate(records, args)

    return {
        "project": None,
        "records": page_records,
        "total": total,
        "page": page,
        "page_size": args["page_size"],
        "pages": pages,
    }


@api_bp.route("/records/<int:id_file>/thumbnail", methods=["GET"])
def record_thumbnail(id_file):
    """
    Serves the low-resolution dashboard/explorer spectrogram thumbnail for
    `id_file` (Phase 2 of the redesign, "Vignettes spectrogramme" - optional
    item). Companion to `has_thumbnail` above: the client should only point an
    `<img>` here when that field is `True` for the record, and fall back to
    the CSS placeholder otherwise.

    Behaviour:
      - already cached (`bucket/spectrograms/<id_file>.png`) -> served as-is.
      - not cached yet, but the record's `.wav` is present on disk -> rendered
        on this request and cached for next time
        (`compute_pipline.generate_thumbnail`). This - not any change to the
        upload/analysis route in `app.py` - is what makes "every future
        upload gets a real thumbnail" true: `pipeline()` also accepts an
        optional `id_file` to pre-render the thumbnail right after analysis
        (see its docstring), but nothing requires that to have happened for
        this route to work.
      - no `.wav` on disk for this record (true for the bulk of the demo
        dataset in this environment, see CLAUDE.md) -> 404, so the client can
        tell it should use the placeholder instead of retrying forever.
    """
    file_row = _get_file_or_404(id_file)

    out_path = thumbnail_path(id_file)
    if not os.path.exists(out_path):
        filepath = os.path.join(file_row["path"], file_row["name"])
        generate_thumbnail(filepath, id_file)

    if not os.path.exists(out_path):
        abort(404, description=f"No spectrogram thumbnail available for record {id_file}.")

    return send_file(out_path, mimetype="image/png")


@api_bp.route("/species", methods=["GET"])
def list_species():
    """All known species, for the explorer's species filter when no single
    project is selected (a per-project species list is still used — see
    `project_stats` — when one is)."""
    species_map = _species_name_map()
    return {
        "species": [
            {"id": id_species, "name": name}
            for id_species, name in sorted(species_map.items(), key=lambda kv: kv[1])
        ]
    }
