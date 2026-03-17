"""Auth API: login and logout."""
from flask import request, jsonify

from api.auth_utils import check_password, encode_jwt, require_auth
from api import api_bp
from models import User


@api_bp.route("/auth/login", methods=["POST"])
def login():
    """POST /api/auth/login — body: { username, password }. Returns user info and JWT."""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or password is None:
        return jsonify({"error": "username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password(password, user.password_hash):
        return jsonify({"error": "Invalid username or password"}), 401

    token = encode_jwt(user)
    return jsonify({
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "restaurant_id": user.restaurant_id,
        },
        "token": token,
    }), 200


@api_bp.route("/auth/logout", methods=["POST"])
@require_auth
def logout():
    """POST /api/auth/logout — invalidate session. Client should discard the token."""
    return jsonify({"message": "Logged out"}), 200
