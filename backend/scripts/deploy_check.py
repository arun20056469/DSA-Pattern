"""Verify the configured DB path and that startup seeding works on it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.database import DB_PATH, engine
from app.seed_loader import load_seed

print(f"DB path: {DB_PATH}")
load_seed()
with engine.connect() as conn:
    patterns = conn.execute(text("SELECT COUNT(*) FROM patterns")).scalar()
    problems = conn.execute(text("SELECT COUNT(*) FROM problems")).scalar()
    progress = conn.execute(text("SELECT COUNT(*) FROM progress")).scalar()
print(f"patterns={patterns} problems={problems} progress={progress}")
