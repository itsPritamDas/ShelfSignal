import os
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, request

from .config import Config
from .extensions import db
from .routes.api import api
from .routes.pages import pages
from .services.data_service import seed_demo_data


def create_app(config_class=Config):
    is_vercel = os.getenv("VERCEL", "").lower() == "1"

    runtime_dir = Path(
        os.getenv(
            "SHELF_SIGNAL_RUNTIME_DIR",
            "/tmp/shelfsignal" if is_vercel else str(Path(__file__).resolve().parent.parent / "instance"),
        )
    )
    runtime_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(
        __name__,
        instance_path=str(runtime_dir / "instance"),
        instance_relative_config=True,
        static_folder=None if is_vercel else "../public/static",
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    # Vercel's deployment bundle is read-only. Runtime caches belong in /tmp.
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["MODEL_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    app.register_blueprint(pages)
    app.register_blueprint(api)

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "File too large. Maximum upload size is 12 MB."}), 413

    # Delay database access until an API request needs it. A missing or invalid
    # database must not crash the Flask function while Vercel imports index.py.
    database_lock = Lock()
    app.extensions["shelfsignal_db_ready"] = False

    @app.before_request
    def ensure_database_ready():
        if not request.path.startswith("/api/") or request.path == "/api/health":
            return None

        if is_vercel and not app.config.get("DATABASE_URL_CONFIGURED", False):
            return jsonify({
                "error": "DATABASE_URL is missing. Add your managed MySQL connection string in Vercel Project Settings > Environment Variables, then redeploy."
            }), 503

        if app.extensions["shelfsignal_db_ready"]:
            return None

        with database_lock:
            if app.extensions["shelfsignal_db_ready"]:
                return None
            try:
                db.create_all()
                seed_enabled = os.getenv(
                    "SHELFSIGNAL_SEED_DEMO",
                    "0" if is_vercel else "1",
                ).lower() in {"1", "true", "yes"}
                if seed_enabled:
                    seeded = seed_demo_data(
                        app.config["DEMO_SALES_FILE"],
                        app.config["DEMO_INVENTORY_FILE"],
                    )
                    if seeded:
                        app.logger.info("Loaded bundled ShelfSignal synthetic demo dataset.")
                app.extensions["shelfsignal_db_ready"] = True
            except Exception:
                db.session.remove()
                app.logger.exception("ShelfSignal database initialisation failed")
                return jsonify({
                    "error": "ShelfSignal could not connect to or initialise its database. Check DATABASE_URL, MySQL network access, and the Vercel Runtime Logs."
                }), 503

        return None

    return app
