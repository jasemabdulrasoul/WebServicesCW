"""Application configuration from environment."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Flask and app configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", os.environ.get("SECRET_KEY", "jwt-secret-key"))
    JWT_EXPIRE = int(os.environ.get("JWT_EXPIRE", 86400))

    # SQLite by default; override with DATABASE_URL for PostgreSQL
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///app.db")

    # Flask-SQLAlchemy expects SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
