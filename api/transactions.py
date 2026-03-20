"""Transactions and purchase order API."""
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import g, jsonify, request

from api import api_bp
from api.auth_utils import require_admin, require_auth
from extensions import db
from models import Customer, MenuItem, Restaurant, Transaction


ALLOWED_STATUSES = {"pending", "accepted", "rejected"}


def _transaction_json(txn: Transaction):
    """Serialize transaction model."""
    return {
        "id": txn.id,
        "customer_id": txn.customer_id,
        "restaurant_id": txn.restaurant_id,
        "amount": float(txn.amount),
        "type": txn.type,
        "status": txn.status,
        "description": txn.description,
        "timestamp": txn.timestamp.isoformat() if txn.timestamp else None,
    }


def _parse_iso_date(value: str):
    """Parse ISO date/time string to datetime; return None if invalid or empty."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@api_bp.route("/transactions", methods=["GET"])
@require_auth
def list_transactions():
    """GET /api/transactions — list with optional filters and pagination."""
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 20, type=int)))

    q = Transaction.query

    customer_id = request.args.get("customer_id", type=int)
    restaurant_id = request.args.get("restaurant_id", type=int)
    status = (request.args.get("status") or "").strip().lower()
    date_from = _parse_iso_date((request.args.get("date_from") or "").strip())
    date_to = _parse_iso_date((request.args.get("date_to") or "").strip())

    if customer_id:
        q = q.filter(Transaction.customer_id == customer_id)
    if restaurant_id:
        q = q.filter(Transaction.restaurant_id == restaurant_id)
    if status:
        q = q.filter(Transaction.status == status)
    if date_from:
        q = q.filter(Transaction.timestamp >= date_from)
    if date_to:
        q = q.filter(Transaction.timestamp <= date_to)

    if g.current_user.role == "restaurant":
        if g.current_user.restaurant_id is None:
            return jsonify({"error": "Restaurant user has no restaurant assigned"}), 403
        q = q.filter(Transaction.restaurant_id == g.current_user.restaurant_id)

    q = q.order_by(Transaction.timestamp.desc(), Transaction.id.desc())
    pagination = q.paginate(page=page, per_page=per_page)
    return jsonify({
        "transactions": [_transaction_json(t) for t in pagination.items],
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
    }), 200


@api_bp.route("/transactions", methods=["POST"])
@require_auth
def create_purchase_transaction():
    """POST /api/transactions — create purchase and deduct customer balance."""
    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    restaurant_id = data.get("restaurant_id")
    items = data.get("items")

    if not isinstance(customer_id, int) or not isinstance(restaurant_id, int):
        return jsonify({"error": "customer_id and restaurant_id must be integers"}), 400
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "items must be a non-empty list"}), 400

    # Role scope check
    if g.current_user.role == "restaurant" and g.current_user.restaurant_id != restaurant_id:
        return jsonify({"error": "Access denied to this restaurant"}), 403

    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    total = Decimal("0")
    for idx, entry in enumerate(items):
        if not isinstance(entry, dict):
            return jsonify({"error": f"items[{idx}] must be an object"}), 400
        menu_item_id = entry.get("menu_item_id")
        quantity = entry.get("quantity")
        if not isinstance(menu_item_id, int) or not isinstance(quantity, int):
            return jsonify({"error": f"items[{idx}] menu_item_id and quantity must be integers"}), 400
        if quantity <= 0:
            return jsonify({"error": f"items[{idx}] quantity must be > 0"}), 400

        menu_item = MenuItem.query.filter_by(id=menu_item_id, restaurant_id=restaurant_id).first()
        if not menu_item:
            return jsonify({"error": f"Menu item {menu_item_id} not found for this restaurant"}), 400
        if menu_item.sold_out:
            return jsonify({"error": f"Menu item {menu_item_id} is sold out"}), 400
        total += menu_item.price * quantity

    if customer.balance < total:
        return jsonify({"error": "Insufficient balance"}), 400

    customer.balance -= total
    txn = Transaction(
        customer_id=customer_id,
        restaurant_id=restaurant_id,
        amount=total,
        type="purchase",
        status="pending",
        description="Purchase order",
    )
    db.session.add(txn)
    db.session.commit()
    return jsonify(_transaction_json(txn)), 201


@api_bp.route("/transactions/<int:transaction_id>", methods=["GET"])
@require_auth
def get_transaction(transaction_id: int):
    """GET /api/transactions/<id> — admin any, restaurant own only."""
    txn = Transaction.query.get(transaction_id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404

    if g.current_user.role == "restaurant" and txn.restaurant_id != g.current_user.restaurant_id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify(_transaction_json(txn)), 200


@api_bp.route("/transactions/<int:transaction_id>", methods=["PATCH"])
@require_auth
def update_transaction_status(transaction_id: int):
    """PATCH /api/transactions/<id> — restaurant can accept/reject own pending purchase."""
    if g.current_user.role != "restaurant":
        return jsonify({"error": "Restaurant access required"}), 403
    if g.current_user.restaurant_id is None:
        return jsonify({"error": "Restaurant user has no restaurant assigned"}), 403

    txn = Transaction.query.get(transaction_id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
    if txn.restaurant_id != g.current_user.restaurant_id:
        return jsonify({"error": "Access denied"}), 403
    if txn.type != "purchase":
        return jsonify({"error": "Only purchase transactions can be updated"}), 400

    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    if status not in {"accepted", "rejected"}:
        return jsonify({"error": "status must be 'accepted' or 'rejected'"}), 400
    if txn.status not in ALLOWED_STATUSES:
        return jsonify({"error": "Transaction status is invalid"}), 400
    if txn.status != "pending":
        return jsonify({"error": "Only pending transactions can be updated"}), 400

    txn.status = status
    db.session.commit()
    return jsonify(_transaction_json(txn)), 200


@api_bp.route("/transactions/<int:transaction_id>", methods=["DELETE"])
@require_admin
def delete_transaction(transaction_id: int):
    """DELETE /api/transactions/<id> — admin only; revert customer balance for supported types."""
    txn = Transaction.query.get(transaction_id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
    if txn.type not in {"purchase", "balance_add", "balance_withdraw"}:
        return jsonify({"error": "Only purchase and balance transactions can be deleted"}), 400

    customer = Customer.query.get(txn.customer_id)
    if not customer:
        return jsonify({"error": "Customer for this transaction not found"}), 404

    # Revert the balance change applied when the transaction was created.
    # - purchase: deducted from balance => add back
    # - balance_add: added to balance => subtract
    # - balance_withdraw: deducted from balance => add back
    if txn.type == "purchase":
        delta = txn.amount
    elif txn.type == "balance_add":
        delta = -txn.amount
    else:  # balance_withdraw
        delta = txn.amount

    if customer.balance + delta < 0:
        return jsonify({"error": "Insufficient balance to revert transaction"}), 400

    customer.balance += delta
    db.session.delete(txn)
    db.session.commit()
    return jsonify({"message": "Transaction deleted and balance reverted"}), 200
