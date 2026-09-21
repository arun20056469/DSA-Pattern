from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Pattern, Problem, Progress, Status

# Leitner-style fixed review intervals (days), indexed by review_count (0-based, capped at last value)
REVIEW_INTERVALS_DAYS = [1, 3, 7, 16, 35]


def get_patterns(db: Session) -> list[Pattern]:
    return list(db.execute(select(Pattern).order_by(Pattern.order_index)).scalars().all())


def get_pattern_by_slug(db: Session, slug: str) -> Pattern | None:
    stmt = (
        select(Pattern)
        .where(Pattern.slug == slug)
        .options(joinedload(Pattern.problems).joinedload(Problem.progress))
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def get_problem(db: Session, problem_id: int) -> Problem | None:
    stmt = (
        select(Problem)
        .where(Problem.id == problem_id)
        .options(joinedload(Problem.progress))
    )
    return db.execute(stmt).scalar_one_or_none()


def list_problems(
    db: Session,
    pattern_slug: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> list[Problem]:
    stmt = select(Problem).join(Pattern).options(
        joinedload(Problem.progress), joinedload(Problem.pattern)
    )
    if pattern_slug:
        stmt = stmt.where(Pattern.slug == pattern_slug)
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    if q:
        stmt = stmt.where(Problem.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Pattern.order_index, Problem.order_index)

    results = list(db.execute(stmt).unique().scalars().all())

    if status:
        filtered = []
        for p in results:
            current_status = p.progress.status.value if p.progress else Status.NOT_STARTED.value
            if current_status == status:
                filtered.append(p)
        results = filtered

    return results


def _next_interval_days(review_count: int) -> int:
    idx = min(review_count, len(REVIEW_INTERVALS_DAYS) - 1)
    return REVIEW_INTERVALS_DAYS[idx]


def update_progress(
    db: Session, problem: Problem, new_status: Status | None, notes: str | None
) -> Progress:
    progress = problem.progress
    if progress is None:
        progress = Progress(
            problem_id=problem.id, status=Status.NOT_STARTED, notes="", review_count=0
        )
        db.add(progress)

    now = datetime.utcnow()

    if notes is not None:
        progress.notes = notes

    if new_status is not None and new_status != progress.status:
        progress.status = new_status
        if new_status == Status.SOLVED:
            progress.solved_at = now
            progress.last_reviewed_at = now
            progress.review_count += 1
            progress.next_review_at = now + timedelta(days=_next_interval_days(progress.review_count - 1))
        elif new_status == Status.ATTEMPTED:
            progress.last_reviewed_at = now
        elif new_status == Status.NOT_STARTED:
            progress.solved_at = None
            progress.next_review_at = None
            progress.review_count = 0

    db.commit()
    db.refresh(progress)
    return progress


def review_problem_again(db: Session, problem: Problem) -> Progress:
    """Mark a solved problem as reviewed today; advances the spaced-repetition schedule."""
    progress = problem.progress
    if progress is None:
        raise ValueError("Problem has no progress record yet")
    now = datetime.utcnow()
    progress.last_reviewed_at = now
    progress.review_count += 1
    progress.next_review_at = now + timedelta(days=_next_interval_days(progress.review_count - 1))
    db.commit()
    db.refresh(progress)
    return progress


def get_dashboard_data(db: Session):
    patterns = get_patterns(db)
    all_problems = list_problems(db)

    total = len(all_problems)
    solved = sum(1 for p in all_problems if p.progress and p.progress.status == Status.SOLVED)
    attempted = sum(1 for p in all_problems if p.progress and p.progress.status == Status.ATTEMPTED)

    now = datetime.utcnow()
    due_for_review = sum(
        1
        for p in all_problems
        if p.progress
        and p.progress.status == Status.SOLVED
        and p.progress.next_review_at is not None
        and p.progress.next_review_at <= now
    )

    by_pattern = []
    for pattern in patterns:
        pattern_problems = [p for p in all_problems if p.pattern_id == pattern.id]
        p_total = len(pattern_problems)
        p_solved = sum(1 for p in pattern_problems if p.progress and p.progress.status == Status.SOLVED)
        p_attempted = sum(
            1 for p in pattern_problems if p.progress and p.progress.status == Status.ATTEMPTED
        )
        by_pattern.append(
            {
                "slug": pattern.slug,
                "name": pattern.name,
                "total": p_total,
                "solved": p_solved,
                "attempted": p_attempted,
                "not_started": p_total - p_solved - p_attempted,
                "percent_solved": round((p_solved / p_total) * 100, 1) if p_total else 0.0,
            }
        )

    by_difficulty: dict[str, dict[str, int]] = {}
    for diff in ("Easy", "Medium", "Hard"):
        diff_problems = [p for p in all_problems if p.difficulty.value == diff]
        diff_solved = sum(1 for p in diff_problems if p.progress and p.progress.status == Status.SOLVED)
        by_difficulty[diff] = {"total": len(diff_problems), "solved": diff_solved}

    solved_dates = sorted(
        {p.progress.solved_at.date() for p in all_problems if p.progress and p.progress.solved_at},
        reverse=True,
    )
    streak = 0
    if solved_dates:
        today = now.date()
        expected = today
        if solved_dates[0] not in (today, today - timedelta(days=1)):
            streak = 0
        else:
            for d in solved_dates:
                if d == expected:
                    streak += 1
                    expected = expected - timedelta(days=1)
                elif d == expected + timedelta(days=1):
                    continue
                else:
                    break

    return {
        "total_problems": total,
        "total_solved": solved,
        "total_attempted": attempted,
        "percent_solved": round((solved / total) * 100, 1) if total else 0.0,
        "current_streak_days": streak,
        "due_for_review": due_for_review,
        "by_pattern": by_pattern,
        "by_difficulty": by_difficulty,
    }
