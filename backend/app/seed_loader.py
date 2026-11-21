import json
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import Difficulty, Pattern, Problem, Stage

SEED_FILE = Path(__file__).resolve().parent / "seed" / "patterns_seed.json"


def _slug_from_url(url: str) -> str | None:
    marker = "/problems/"
    if marker not in url:
        return None
    return url.split(marker, 1)[1].strip("/").split("?", 1)[0] or None


def load_seed(seed_path: Path = SEED_FILE) -> None:
    """Idempotently load patterns/problems from a JSON seed file into the DB.

    Existing patterns/problems (matched by slug) are updated in place rather than
    duplicated, so this is safe to re-run any time the seed file changes.
    """
    Base.metadata.create_all(bind=engine)

    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        for pattern_data in data["patterns"]:
            pattern = db.query(Pattern).filter_by(slug=pattern_data["slug"]).first()
            if pattern is None:
                pattern = Pattern(slug=pattern_data["slug"])
                db.add(pattern)

            pattern.name = pattern_data["name"]
            pattern.stage = Stage(pattern_data.get("stage", "Basic"))
            pattern.order_index = pattern_data["order"]
            pattern.short_description = pattern_data["short_description"]
            pattern.when_to_use = pattern_data["when_to_use"]
            pattern.recognition_tips = pattern_data["recognition_tips"]
            pattern.complexity = pattern_data["complexity"]
            pattern.template_code = pattern_data["template_code"]
            db.flush()  # ensure pattern.id is populated

            for problem_data in pattern_data.get("problems", []):
                problem = (
                    db.query(Problem)
                    .filter_by(pattern_id=pattern.id, slug=problem_data["slug"])
                    .first()
                )
                if problem is None:
                    problem = Problem(pattern_id=pattern.id, slug=problem_data["slug"])
                    db.add(problem)

                problem.name = problem_data["name"]
                problem.difficulty = Difficulty(problem_data["difficulty"])
                problem.leetcode_url = problem_data["leetcode_url"]
                problem.leetcode_id = problem_data.get("leetcode_id")
                problem.leetcode_slug = problem_data.get("leetcode_slug") or _slug_from_url(
                    problem_data["leetcode_url"]
                )
                problem.tags = ",".join(problem_data.get("tags", [])) or None
                problem.hint = problem_data["hint"]
                problem.order_index = problem_data["order"]

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    load_seed()
    print(f"Seed loaded from {SEED_FILE}")
