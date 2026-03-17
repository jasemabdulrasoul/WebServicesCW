"""Flask application entrypoint. All API routes are mounted under /api."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    """Create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from api import api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        import models  # noqa: F401 - register models with db
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
