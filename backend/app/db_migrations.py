"""Small Alembic wrapper used at app startup.

The original app created its tables with ``Base.metadata.create_all()`` and had
no migration history.  This module stamps that schema as the baseline revision
and then applies any newer revisions.  Fresh databases are created by
``load_seed()`` and stamped at head once their tables exist.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import SQLALCHEMY_DATABASE_URL, engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BACKEND_DIR / "alembic.ini"


def _config() -> Config:
    cfg = Config(str(CONFIG_PATH))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL.replace("%", "%%"))
    return cfg


def _has_table(name: str) -> bool:
    return inspect(engine).has_table(name)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in inspect(engine).get_columns(table)}


def run_migrations() -> bool:
    """Apply migrations. Returns False when the DB is fresh (no tables yet)."""
    cfg = _config()

    if not _has_table("patterns"):
        # Fresh DB: load_seed() will create the current schema via create_all().
        return False

    if not _has_table("alembic_version"):
        if _has_column("patterns", "stage"):
            # Already at the current schema (e.g. recreated from models).
            command.stamp(cfg, "head")
        else:
            # Legacy schema created by create_all() before migrations existed.
            command.stamp(cfg, "0001_baseline")

    command.upgrade(cfg, "head")
    return True


def stamp_fresh_head() -> None:
    """Mark a freshly created DB as fully migrated (called after create_all)."""
    if _has_table("alembic_version"):
        return
    command.stamp(_config(), "head")
