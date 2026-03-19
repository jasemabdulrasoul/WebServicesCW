"""Menu API under restaurant scope."""
from decimal import Decimal, InvalidOperation

from flask import g, jsonify, request

from api import api_bp
from api.auth_utils import require_auth
from extensions import db
from models import MenuItem, Restaurant


def _can_access_restaurant(restaurant_id: int) -> bool:
    """Admin can access any restaurant; restaurant role can access only own."""
    if g.current_user.role == "admin":
        return True
    return g.current_user.role == "restaurant" and g.current_user.restaurant_id == restaurant_id


def _menu_item_json(item: MenuItem):
    """Serialize menu item."""
    return {
        "id": item.id,
        "restaurant_id": item.restaurant_id,
        "name": item.name,
        "price": float(item.price),
        "sold_out": item.sold_out,
    }


@api_bp.route("/restaurants/<int:restaurant_id>/menu", methods=["GET"])
@require_auth
def list_menu_items(restaurant_id: int):
    """GET /api/restaurants/<restaurant_id>/menu — list menu items."""
    if not _can_access_restaurant(restaurant_id):
        return jsonify({"error": "Access denied"}), 403
    if not Restaurant.query.get(restaurant_id):
        return jsonify({"error": "Restaurant not found"}), 404

    items = MenuItem.query.filter_by(restaurant_id=restaurant_id).order_by(MenuItem.id).all()
    return jsonify({"menu_items": [_menu_item_json(i) for i in items]}), 200


@api_bp.route("/restaurants/<int:restaurant_id>/menu", methods=["POST"])
@require_auth
def create_menu_item(restaurant_id: int):
    """POST /api/restaurants/<restaurant_id>/menu — add menu item."""
    if not _can_access_restaurant(restaurant_id):
        return jsonify({"error": "Access denied"}), 403
    if not Restaurant.query.get(restaurant_id):
        return jsonify({"error": "Restaurant not found"}), 404

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    sold_out = bool(data.get("sold_out", False))
    try:
        price = Decimal(str(data.get("price", "")))
    except (InvalidOperation, ValueError):
        return jsonify({"error": "price must be a valid number"}), 400

    if not name:
        return jsonify({"error": "name is required"}), 400
    if price <= 0:
        return jsonify({"error": "price must be positive"}), 400

    item = MenuItem(restaurant_id=restaurant_id, name=name, price=price, sold_out=sold_out)
    db.session.add(item)
    db.session.commit()
    return jsonify(_menu_item_json(item)), 201


@api_bp.route("/restaurants/<int:restaurant_id>/menu/<int:menu_id>", methods=["GET"])
@require_auth
def get_menu_item(restaurant_id: int, menu_id: int):
    """GET /api/restaurants/<restaurant_id>/menu/<menu_id> — get one item."""
    if not _can_access_restaurant(restaurant_id):
        return jsonify({"error": "Access denied"}), 403

    item = MenuItem.query.filter_by(id=menu_id, restaurant_id=restaurant_id).first()
    if not item:
        return jsonify({"error": "Menu item not found"}), 404
    return jsonify(_menu_item_json(item)), 200


@api_bp.route("/restaurants/<int:restaurant_id>/menu/<int:menu_id>", methods=["PATCH"])
@require_auth
def update_menu_item(restaurant_id: int, menu_id: int):
    """PATCH /api/restaurants/<restaurant_id>/menu/<menu_id> — update item fields."""
    if not _can_access_restaurant(restaurant_id):
        return jsonify({"error": "Access denied"}), 403

    item = MenuItem.query.filter_by(id=menu_id, restaurant_id=restaurant_id).first()
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        item.name = name
    if "price" in data:
        try:
            price = Decimal(str(data.get("price")))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "price must be a valid number"}), 400
        if price <= 0:
            return jsonify({"error": "price must be positive"}), 400
        item.price = price
    if "sold_out" in data:
        item.sold_out = bool(data.get("sold_out"))

    db.session.commit()
    return jsonify(_menu_item_json(item)), 200


@api_bp.route("/restaurants/<int:restaurant_id>/menu/<int:menu_id>", methods=["DELETE"])
@require_auth
def delete_menu_item(restaurant_id: int, menu_id: int):
    """DELETE /api/restaurants/<restaurant_id>/menu/<menu_id> — delete menu item."""
    if not _can_access_restaurant(restaurant_id):
        return jsonify({"error": "Access denied"}), 403

    item = MenuItem.query.filter_by(id=menu_id, restaurant_id=restaurant_id).first()
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Menu item deleted"}), 200
