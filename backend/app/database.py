import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# backend/app/database.py -> project root is two levels up from this file's parent (backend/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

# Deployments mount a persistent volume and set DSA_DB_PATH to a path on it
# (for example /data/dsa.db). Relative paths are resolved from the project root.
_configured_path = os.environ.get("DSA_DB_PATH")
if _configured_path:
    candidate = Path(_configured_path).expanduser()
    DB_PATH = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
else:
    DB_PATH = DEFAULT_DATA_DIR / "dsa.db"

DATA_DIR = DB_PATH.parent
DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
