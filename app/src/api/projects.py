"""
Phase 2 of the redesign (see docs/redesign/ROADMAP.md): project-scoped stats and
a filtered/paginated record listing, consumed client-side (fetch) by the new
dashboard (`/dashboard`) and explorer (`/files`) templates. No HTML is rendered
here; `app.py` only renders the page shells, all data comes from this module.

Routes defined here:
    GET /api/projects                       - project picker (id, name, file_count)
    GET /api/projects/<id>/stats             - dashboard summary cards
    GET /api/projects/<id>/records           - explorer listing (search/filter/sort/paginate)

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

from flask import abort, request

from . import api_bp
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


@api_bp.route("/projects/<int:id_project>/records", methods=["GET"])
def project_records(id_project):
    """
    Filtered/sorted/paginated record listing for the explorer (`/files`).

    Query params (all optional):
        q: case-insensitive substring match on the record name.
        species: id_species, keep only records with at least one detection of
            that species.
        status: one of 'new', 'pending', 'reviewed' (see `_record_status`).
        date_from, date_to: 'YYYY-MM-DD', inclusive, filtered on FILES.date.
        sort: 'name' | 'date' | 'detections' | 'duration' (default 'date').
        dir: 'asc' | 'desc' (default 'desc').
        page: 1-based page number (default 1).
        page_size: rows per page (default 10, max 100).
    """
    project = _get_project_or_404(id_project)

    q = (request.args.get("q") or "").strip().lower()
    species_filter = request.args.get("species", type=int)
    status_filter = request.args.get("status")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    sort = request.args.get("sort", default="date")
    direction = request.args.get("dir", default="desc")
    page = max(1, request.args.get("page", default=1, type=int) or 1)
    page_size = request.args.get("page_size", default=10, type=int) or 10
    page_size = max(1, min(page_size, 100))

    if status_filter not in (None, "new", "pending", "reviewed"):
        abort(400, description="`status` must be one of 'new', 'pending', 'reviewed'.")
    if sort not in ("name", "date", "detections", "duration"):
        abort(400, description="`sort` must be one of 'name', 'date', 'detections', 'duration'.")

    Database.open_connexion()
    try:
        files = _as_list(Database.get_files(
            id_project=id_project,
            time_min=date_from,
            time_max=date_to,
        ))
    finally:
        Database.close_connexion()

    id_files = [f["id_file"] for f in files]
    detections_by_file = _detections_by_file(id_files) if id_files else {}
    species_map = _species_name_map()

    records = []
    for f in files:
        if q and q not in f["name"].lower():
            continue

        dets = detections_by_file.get(f["id_file"], [])
        species_ids = sorted({d["id_species"] for d in dets})

        if species_filter is not None and species_filter not in species_ids:
            continue

        status = _record_status(dets)
        if status_filter and status != status_filter:
            continue

        pending = sum(1 for d in dets if d["review_status"] == "pending")
        records.append({
            "id": f["id_file"],
            "name": f["name"],
            "project_name": project["name"],
            "date": f["date"].isoformat() if f["date"] else None,
            "duration_seconds": f["duration"],
            "detections": len(dets),
            "pending_detections": pending,
            "species": [species_map.get(i, f"Species {i}") for i in species_ids],
            "status": status,
        })

    sort_key = {
        "name": lambda r: r["name"],
        "date": lambda r: r["date"] or "",
        "detections": lambda r: r["detections"],
        "duration": lambda r: r["duration_seconds"] or 0,
    }[sort]
    records.sort(key=sort_key, reverse=(direction != "asc"))

    total = len(records)
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    start = (page - 1) * page_size
    page_records = records[start:start + page_size]

    return {
        "project": {"id": project["id_project"], "name": project["name"]},
        "records": page_records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
