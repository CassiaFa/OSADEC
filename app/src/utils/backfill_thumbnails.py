"""
One-off backfill for the Phase 2 dashboard/explorer thumbnails (see
docs/redesign/ROADMAP.md): generates `bucket/spectrograms/<id_file>.png` for
every `FILES` row whose `.wav` is actually present on disk, skipping records
that already have a cached thumbnail.

Not wired into any route or scheduled job - thumbnails for *future* uploads
are handled automatically, lazily, by `GET /api/records/<id>/thumbnail`
(`app/src/api/projects.py`) the first time they're requested, and optionally
pre-warmed right after analysis by `pipeline(..., id_file=...)`
(`compute_pipline.py`). This script only exists to backfill records that were
analysed *before* that lazy route existed, so their thumbnail isn't left to
whenever a dashboard/explorer page happens to request it first.

Usage (inside the app container, cwd `/osadec` so the `bucket/`-relative
paths used elsewhere in this module resolve the same way):

    python -m src.utils.backfill_thumbnails
"""

import os

from .compute_pipline import generate_thumbnail, thumbnail_path
from .db_tools import Database


def backfill():
    Database.open_connexion()
    try:
        files = Database.get_files()
    finally:
        Database.close_connexion()

    if isinstance(files, dict):
        files = [files]

    generated, skipped_cached, skipped_missing = 0, 0, 0

    for f in files or []:
        id_file = f["id_file"]
        if os.path.exists(thumbnail_path(id_file)):
            skipped_cached += 1
            continue

        filepath = os.path.join(f["path"], f["name"])
        if not os.path.exists(filepath):
            skipped_missing += 1
            continue

        out = generate_thumbnail(filepath, id_file)
        if out:
            print(f"id_file={id_file}: generated {out}")
            generated += 1
        else:
            print(f"id_file={id_file}: generation failed (see above)")

    print(
        f"Done: {generated} generated, {skipped_cached} already cached, "
        f"{skipped_missing} no .wav on disk."
    )


if __name__ == "__main__":
    backfill()
