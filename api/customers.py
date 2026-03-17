"""Customers API: CRUD and balance. Admin only (except GET one for order flow)."""
from decimal import Decimal

from flask import request, jsonify
from sqlalchemy import or_

from api import api_bp
from api.auth_utils import require_admin
from extensions import db
from models import Customer, Transaction


def _customer_json(c):
    """Serialize a Customer to JSON."""
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "balance": float(c.balance),
    }


@api_bp.route("/customers", methods=["GET"])
@require_admin
def list_customers():
    """GET /api/customers — list with optional search, page, per_page."""
    search = (request.args.get("search") or "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 20, type=int)))

    q = Customer.query
    if search:
        q = q.filter(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )
    q = q.order_by(Customer.id)
    pagination = q.paginate(page=page, per_page=per_page)

    return jsonify({
        "customers": [_customer_json(c) for c in pagination.items],
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
    }), 200


@api_bp.route("/customers", methods=["POST"])
@require_admin
def create_customer():
    """POST /api/customers — create with name, phone; initial balance 0."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip() or None

    if not name:
        return jsonify({"error": "name is required"}), 400

    customer = Customer(name=name, phone=phone, balance=Decimal("0"))
    db.session.add(customer)
    db.session.commit()
    return jsonify(_customer_json(customer)), 201


@api_bp.route("/customers/<int:customer_id>", methods=["GET"])
@require_admin
def get_customer(customer_id):
    """GET /api/customers/<id> — get one."""
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify(_customer_json(customer)), 200


@api_bp.route("/customers/<int:customer_id>", methods=["PATCH"])
@require_admin
def update_customer(customer_id):
    """PATCH /api/customers/<id> — update name, phone."""
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        customer.name = name
    if "phone" in data:
        customer.phone = (data.get("phone") or "").strip() or None

    db.session.commit()
    return jsonify(_customer_json(customer)), 200


@api_bp.route("/customers/<int:customer_id>", methods=["DELETE"])
@require_admin
def delete_customer(customer_id):
    """DELETE /api/customers/<id>."""
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": "Customer deleted"}), 200


@api_bp.route("/customers/<int:customer_id>/balance", methods=["POST"])
@require_admin
def customer_balance(customer_id):
    """POST /api/customers/<id>/balance — body: { amount, action: 'add' | 'withdraw' }. No negative balance."""
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        amount = Decimal(str(data.get("amount", 0)))
    except Exception:
        return jsonify({"error": "amount must be a number"}), 400
    action = (data.get("action") or "").strip().lower()

    if amount <= 0:
        return jsonify({"error": "amount must be positive"}), 400
    if action not in ("add", "withdraw"):
        return jsonify({"error": "action must be 'add' or 'withdraw'"}), 400

    if action == "withdraw":
        if customer.balance < amount:
            return jsonify({"error": "Insufficient balance"}), 400
        customer.balance -= amount
        txn_type = "balance_withdraw"
    else:
        customer.balance += amount
        txn_type = "balance_add"

    txn = Transaction(
        customer_id=customer.id,
        restaurant_id=None,
        amount=amount,
        type=txn_type,
        status="accepted",
        description=f"Balance {action}",
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify(_customer_json(customer)), 200
