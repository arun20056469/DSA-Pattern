"""CLI tool to bulk-import extra problems from a CSV file.

Usage:
    python -m app.import_csv path/to/problems.csv

Expected CSV columns (header row required):
    pattern_slug   - slug of an existing pattern (e.g. "two-pointers"), or a new one
    pattern_name   - required only when pattern_slug does not exist yet
    name           - problem name, e.g. "Two Sum"
    slug           - optional; auto-generated from `name` if omitted
    difficulty     - Easy | Medium | Hard
    leetcode_url   - direct LeetCode URL
    hint           - one-line hint
    order          - optional integer ordering within the pattern (appended to end if omitted)
"""

import csv
import sys
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import Difficulty, Pattern, Problem


def slugify(name: str) -> str:
    return name.lower().strip().replace(" ", "-").replace("'", "").replace(",", "")


def import_csv(csv_path: Path) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added, updated = 0, 0
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pattern_slug = row["pattern_slug"].strip()
                pattern = db.query(Pattern).filter_by(slug=pattern_slug).first()
                if pattern is None:
                    pattern_name = row.get("pattern_name", "").strip()
                    if not pattern_name:
                        raise ValueError(
                            f"Unknown pattern_slug '{pattern_slug}' and no pattern_name given to create it."
                        )
                    max_order = db.query(Pattern).count()
                    pattern = Pattern(
                        slug=pattern_slug,
                        name=pattern_name,
                        order_index=max_order + 1,
                        short_description="",
                        when_to_use="",
                        recognition_tips="",
                        complexity="",
                        template_code="",
                    )
                    db.add(pattern)
                    db.flush()

                name = row["name"].strip()
                slug = row.get("slug", "").strip() or slugify(name)

                problem = db.query(Problem).filter_by(pattern_id=pattern.id, slug=slug).first()
                is_new = problem is None
                if is_new:
                    max_order = (
                        db.query(Problem).filter_by(pattern_id=pattern.id).count()
                    )
                    problem = Problem(pattern_id=pattern.id, slug=slug, order_index=max_order + 1)
                    db.add(problem)

                problem.name = name
                problem.difficulty = Difficulty(row["difficulty"].strip())
                problem.leetcode_url = row["leetcode_url"].strip()
                problem.hint = row.get("hint", "").strip()
                if row.get("order", "").strip():
                    problem.order_index = int(row["order"])

                added += 1 if is_new else 0
                updated += 0 if is_new else 1

        db.commit()
        print(f"Import complete: {added} problems added, {updated} updated.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.import_csv path/to/problems.csv")
        sys.exit(1)
    import_csv(Path(sys.argv[1]))
