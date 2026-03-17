"""Shared Flask extensions (e.g. db). Defined here to avoid circular imports."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
