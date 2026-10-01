"""
Skeleton for the OSADEC JSON API.

Mounted under the `/api` prefix via `init_api(app)`, called once from `app.py`.
This is intentionally minimal (Phase 0 of the redesign, see
docs/redesign/ROADMAP.md): it only wires up the blueprint, consistent JSON error
responses for anything under `/api/...`, and a `GET /api/health` probe to verify
the blueprint is mounted. Business endpoints (projects, files, detections,
spectrogram, ...) are added in later phases, as separate routes on `api_bp`.
"""

from flask import Blueprint, jsonify, request

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _json_error(status_code, error, message):
    response = jsonify({"error": error, "message": message})
    response.status_code = status_code
    return response


@api_bp.route("/health", methods=["GET"])
def health():
    """Liveness probe: confirms the /api blueprint is mounted and reachable."""
    return jsonify({"status": "ok"})


def _is_api_path(path):
    prefix = api_bp.url_prefix or ""
    return path == prefix or path.startswith(f"{prefix}/")


def init_api(app):
    """
    Registers the `/api` blueprint on `app` and makes sure 400/404/500 responses
    for any `/api/...` path are JSON instead of Flask's default HTML error pages.
    Requests outside `/api` are left untouched (handled by Flask/Jinja as before).
    """

    app.register_blueprint(api_bp)

    @app.errorhandler(404)
    def _api_404(error):
        if _is_api_path(request.path):
            return _json_error(404, "not_found", "The requested resource was not found.")
        return error

    @app.errorhandler(400)
    def _api_400(error):
        if _is_api_path(request.path):
            message = getattr(error, "description", None) or "Bad request."
            return _json_error(400, "bad_request", message)
        return error

    @app.errorhandler(500)
    def _api_500(error):
        if _is_api_path(request.path):
            return _json_error(500, "server_error", "Internal server error.")
        return error
