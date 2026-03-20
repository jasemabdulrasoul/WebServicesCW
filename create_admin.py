"""
CLI script to create the first admin user.

Usage:
  python create_admin.py --username admin --password "your_password"
"""
import argparse
import getpass

from app import create_app
from api.auth_utils import hash_password
from extensions import db
from models import User


def main():
    parser = argparse.ArgumentParser(description="Create the first admin user.")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--password", required=False, help="Admin password (will prompt if omitted)")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        if not password:
            raise SystemExit("Password cannot be empty.")

    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(username=args.username).first()
        if existing:
            raise SystemExit(f"User '{args.username}' already exists (id={existing.id}).")

        admin = User(
            username=args.username,
            password_hash=hash_password(password),
            role="admin",
            restaurant_id=None,
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin user '{admin.username}' (id={admin.id}).")


if __name__ == "__main__":
    main()

