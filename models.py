"""SQLAlchemy models. Import db from extensions to avoid circular import."""
from datetime import datetime

from extensions import db


class User(db.Model):
    """User with role: admin or restaurant. restaurant_id required when role is restaurant."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' | 'restaurant'
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=True)

    restaurant = db.relationship("Restaurant", backref=db.backref("users", lazy="dynamic"))

    def __repr__(self):
        return f"<User {self.username}>"


class Customer(db.Model):
    """Customer with name, phone, and balance."""

    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    balance = db.Column(db.Numeric(12, 2), default=0, nullable=False)

    def __repr__(self):
        return f"<Customer {self.name}>"


class Restaurant(db.Model):
    """Restaurant (booth/vendor)."""

    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"<Restaurant {self.name}>"


class MenuItem(db.Model):
    """Menu item belonging to a restaurant. No options; price and sold_out only."""

    __tablename__ = "menu_items"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    sold_out = db.Column(db.Boolean, default=False, nullable=False)

    restaurant = db.relationship("Restaurant", backref=db.backref("menu_items", lazy="dynamic"))

    def __repr__(self):
        return f"<MenuItem {self.name}>"


class Transaction(db.Model):
    """Transaction: purchase, balance_add, or balance_withdraw. Status: pending, accepted, rejected."""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=True)  # null for balance ops
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'purchase' | 'balance_add' | 'balance_withdraw'
    status = db.Column(db.String(20), nullable=False)  # 'pending' | 'accepted' | 'rejected'
    description = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    customer = db.relationship("Customer", backref=db.backref("transactions", lazy="dynamic"))
    restaurant = db.relationship("Restaurant", backref=db.backref("transactions", lazy="dynamic"))

    def __repr__(self):
        return f"<Transaction {self.id} {self.type} {self.status}>"
