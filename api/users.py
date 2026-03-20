"""Users API (admin only)."""

from flask import jsonify, request
from werkzeug.security import generate_password_hash

from api import api_bp
from api.auth_utils import require_admin
from extensions import db
from models import Restaurant, User


def _user_json(u: User):
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "restaurant_id": u.restaurant_id,
    }


@api_bp.route("/users", methods=["GET"])
@require_admin
def list_users():
    users = User.query.order_by(User.id).all()
    return jsonify({"users": [_user_json(u) for u in users]}), 200


@api_bp.route("/users", methods=["POST"])
@require_admin
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")
    role = (data.get("role") or "").strip().lower()
    restaurant_id = data.get("restaurant_id")

    if not username:
        return jsonify({"error": "username is required"}), 400
    if password is None or password == "":
        return jsonify({"error": "password is required"}), 400
    if role not in {"admin", "restaurant"}:
        return jsonify({"error": "role must be 'admin' or 'restaurant'"}), 400

    if role == "restaurant":
        if restaurant_id is None:
            return jsonify({"error": "restaurant_id is required for restaurant role"}), 400
        try:
            restaurant_id = int(restaurant_id)
        except (TypeError, ValueError):
            return jsonify({"error": "restaurant_id must be an integer"}), 400
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({"error": "restaurant not found"}), 404
    else:
        restaurant_id = None

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 400

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role,
        restaurant_id=restaurant_id,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(_user_json(user)), 201


@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"}), 200

