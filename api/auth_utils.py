"""Auth helpers: password hashing, JWT encode/decode, and auth decorators."""
import functools
import time

import jwt
from flask import current_app, g, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from models import User


def hash_password(password: str) -> str:
    """Return a password hash for storage."""
    return generate_password_hash(password)


def check_password(password: str, password_hash: str) -> bool:
    """Return True if password matches the hash."""
    return check_password_hash(password_hash, password)


def encode_jwt(user: User) -> str:
    """Build a JWT for the user. Payload: sub=user_id, role, restaurant_id, exp."""
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "restaurant_id": user.restaurant_id,
        "exp": int(time.time()) + current_app.config["JWT_EXPIRE"],
    }
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )


def decode_jwt(token: str):
    """Decode JWT and return payload dict or None if invalid."""
    try:
        return jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        return None


def get_token_from_request():
    """Extract Bearer token from Authorization header. Returns None if missing or invalid format."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip() or None


def load_current_user():
    """If valid JWT in request, set g.current_user and return True; else return False."""
    token = get_token_from_request()
    if not token:
        return False
    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        return False
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return False
    user = User.query.get(user_id)
    if not user:
        return False
    g.current_user = user
    return True


def require_auth(f):
    """Decorator: require valid JWT; set g.current_user. Return 401 JSON if not authenticated."""

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not load_current_user():
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return wrapped


def require_admin(f):
    """Decorator: require auth and role admin. Return 403 if not admin."""

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not load_current_user():
            return jsonify({"error": "Authentication required"}), 401
        if g.current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return wrapped


def require_restaurant(f):
    """Decorator: require auth and role restaurant. Return 403 if not restaurant."""

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not load_current_user():
            return jsonify({"error": "Authentication required"}), 401
        if g.current_user.role != "restaurant":
            return jsonify({"error": "Restaurant access required"}), 403
        if g.current_user.restaurant_id is None:
            return jsonify({"error": "Restaurant user has no restaurant assigned"}), 403
        return f(*args, **kwargs)

    return wrapped


def require_admin_or_restaurant_own(restaurant_id_getter):
    """
    Decorator factory: require auth and either admin or restaurant owning the resource.
    restaurant_id_getter is a callable (request_or_id) that returns the restaurant_id to check.
    Usage: @require_admin_or_restaurant_own(lambda: request.view_args['restaurant_id'])
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            if not load_current_user():
                return jsonify({"error": "Authentication required"}), 401
            if g.current_user.role == "admin":
                return f(*args, **kwargs)
            if g.current_user.role != "restaurant":
                return jsonify({"error": "Access denied"}), 403
            rid = restaurant_id_getter()
            if rid is None or g.current_user.restaurant_id != int(rid):
                return jsonify({"error": "Access denied to this resource"}), 403
            return f(*args, **kwargs)

        return wrapped

    return decorator
