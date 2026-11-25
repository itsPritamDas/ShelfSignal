import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = os.getenv("VERCEL", "").lower() == "1"
RUNTIME_DIR = Path(
    os.getenv(
        "SHELF_SIGNAL_RUNTIME_DIR",
        "/tmp/shelfsignal" if IS_VERCEL else str(BASE_DIR / "instance"),
    )
)

raw_database_url = os.getenv("DATABASE_URL", "").strip()
database_url = raw_database_url or (
    f"sqlite:///{(RUNTIME_DIR / 'shelfsignal.db').as_posix()}"
    if IS_VERCEL
    else "sqlite:///shelfsignal.db"
)

# Some managed MySQL providers supply mysql:// URLs; use the PyMySQL driver.
if database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "local-only-change-this-secret")
    SQLALCHEMY_DATABASE_URI = database_url
    DATABASE_URL_CONFIGURED = bool(raw_database_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    BASE_DIR = BASE_DIR
    DEMO_SALES_FILE = BASE_DIR / "data" / "demo_sales.csv"
    DEMO_INVENTORY_FILE = BASE_DIR / "data" / "demo_inventory.csv"
    MODEL_DIR = Path(os.getenv("MODEL_DIR", str(RUNTIME_DIR / "models")))
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(RUNTIME_DIR / "uploads")))
