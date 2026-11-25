
import os
from pathlib import Path

from flask import Flask, jsonify

from .config import Config
from .extensions import db
from .routes.api import api
from .routes.pages import pages
from .services.data_service import seed_demo_data


def create_app(config_class=Config):
    # Detect whether the application is running on Vercel.
    is_vercel = os.getenv("VERCEL") == "1"

    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=None if is_vercel else "../public/static",
        static_url_path="/static"
    )

    # Load application configuration.
    app.config.from_object(config_class)

    # Create runtime directories.
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["MODEL_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    # Initialize SQLAlchemy exactly once.
    db.init_app(app)

    # Register application routes.
    app.register_blueprint(pages)
    app.register_blueprint(api)

    # Handle oversized CSV uploads.
    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({
            "error": "File too large. Maximum upload size is 12 MB."
        }), 413

    # Initialize database tables and optionally load sample data.
    with app.app_context():
        db.create_all()

        seed_enabled = os.getenv(
            "SHELFSIGNAL_SEED_DEMO",
            "0" if is_vercel else "1"
        ).lower() in {"1", "true", "yes"}

        if seed_enabled:
            try:
                seeded = seed_demo_data(
                    app.config["DEMO_SALES_FILE"],
                    app.config["DEMO_INVENTORY_FILE"]
                )

                if seeded:
                    app.logger.info(
                        "Loaded bundled ShelfSignal demo dataset."
                    )

            except Exception:
                app.logger.exception("Could not seed demo data")
                raise

    return app
