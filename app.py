"""Flask application entrypoint. All API routes are mounted under /api."""
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import db


def create_app(config_class=Config):
    """Create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from api import api_bp
    app.register_blueprint(api_bp)

    # Ensure the API consistently returns JSON errors.
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        if request.path.startswith("/api"):
            return jsonify({"error": e.description}), e.code or 400
        return e

    @app.errorhandler(Exception)
    def handle_exception(e: Exception):
        if request.path.startswith("/api"):
            return jsonify({"error": "Internal Server Error"}), 500
        raise

    with app.app_context():
        import models  # noqa: F401 - register models with db
        db.create_all()

    # Frontend pages (API remains JSON-only under /api)
    @app.route("/")
    def home_page():
        return render_template("index.html")

    @app.route("/customers")
    def customers_page():
        return render_template("customers.html")

    @app.route("/purchase")
    def purchase_page():
        return render_template("purchase.html")

    @app.route("/transactions")
    def transactions_page():
        return render_template("transactions.html")

    @app.route("/admin/booths")
    def booths_admin_page():
        return render_template("admin_booths.html")

    @app.route("/admin/users")
    def users_admin_page():
        return render_template("admin_users.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
