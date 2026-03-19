"""Restaurants API: admin full access, restaurant users limited to own restaurant."""
from flask import g, jsonify, request

from api import api_bp
from api.auth_utils import require_admin, require_auth
from extensions import db
from models import Restaurant


def _restaurant_json(restaurant: Restaurant):
    """Serialize a restaurant object."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
    }


def _can_access_restaurant(restaurant_id: int) -> bool:
    """Admin can access any restaurant; restaurant role can access only own."""
    if g.current_user.role == "admin":
        return True
    return g.current_user.role == "restaurant" and g.current_user.restaurant_id == restaurant_id


@api_bp.route("/restaurants", methods=["GET"])
@require_auth
def list_restaurants():
    """GET /api/restaurants — list all (admin) or own restaurant (restaurant user)."""
    if g.current_user.role == "admin":
        restaurants = Restaurant.query.order_by(Restaurant.id).all()
        return jsonify({"restaurants": [_restaurant_json(r) for r in restaurants]}), 200

    if g.current_user.role == "restaurant":
        if g.current_user.restaurant_id is None:
            return jsonify({"error": "Restaurant user has no restaurant assigned"}), 403
        restaurant = Restaurant.query.get(g.current_user.restaurant_id)
        if not restaurant:
            return jsonify({"restaurants": []}), 200
        return jsonify({"restaurants": [_restaurant_json(restaurant)]}), 200

    return jsonify({"error": "Access denied"}), 403


@api_bp.route("/restaurants", methods=["POST"])
@require_admin
def create_restaurant():
    """POST /api/restaurants — create restaurant (admin only)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    restaurant = Restaurant(name=name)
    db.session.add(restaurant)
    db.session.commit()
    return jsonify(_restaurant_json(restaurant)), 201


@api_bp.route("/restaurants/<int:restaurant_id>", methods=["GET"])
@require_auth
def get_restaurant(restaurant_id: int):
    """GET /api/restaurants/<id> — admin any, restaurant own only."""
    if not _can_access_restaurant(restaurant_id):
        return jsonify({"error": "Access denied"}), 403

    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    return jsonify(_restaurant_json(restaurant)), 200


@api_bp.route("/restaurants/<int:restaurant_id>", methods=["PATCH"])
@require_auth
def update_restaurant(restaurant_id: int):
    """PATCH /api/restaurants/<id> — admin any or restaurant own only."""
    if not _can_access_restaurant(restaurant_id):
        return jsonify({"error": "Access denied"}), 403

    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        restaurant.name = name

    db.session.commit()
    return jsonify(_restaurant_json(restaurant)), 200


@api_bp.route("/restaurants/<int:restaurant_id>", methods=["DELETE"])
@require_admin
def delete_restaurant(restaurant_id: int):
    """DELETE /api/restaurants/<id> — admin only."""
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    db.session.delete(restaurant)
    db.session.commit()
    return jsonify({"message": "Restaurant deleted"}), 200
