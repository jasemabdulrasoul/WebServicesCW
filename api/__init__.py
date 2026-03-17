"""API blueprint: all REST endpoints under /api."""
from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/", methods=["GET"])
def index():
    """Health check / API root."""
    return jsonify({"status": "ok", "message": "API is running"}), 200


# Register auth routes (login, logout) on api_bp
from api import auth  # noqa: E402, F401
