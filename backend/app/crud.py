from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Difficulty, Pattern, Problem, Progress, Stage, Status

# Leitner-style fixed review intervals (days), indexed by review_count (0-based, capped at last value)
REVIEW_INTERVALS_DAYS = [1, 3, 7, 16, 35]


def parse_stage(value: str | None) -> Stage | None:
    """Accept either display values (Advanced) or enum names (ADVANCED)."""
    if not value:
        return None
    try:
        return Stage(value)
    except ValueError:
        return Stage[value.upper()]


def get_patterns(db: Session, stage: str | None = None) -> list[Pattern]:
    stmt = select(Pattern)
    stage_enum = parse_stage(stage)
    if stage_enum:
        stmt = stmt.where(Pattern.stage == stage_enum)
    stmt = stmt.order_by(Pattern.order_index)
    return list(db.execute(stmt).scalars().all())


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


def query_problems(
    db: Session,
    pattern_slug: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    q: str | None = None,
    stage: str | None = None,
    tag: str | None = None,
    sort: str = "order",
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[Problem], int]:
    """Filter problems and return (items, total) for pagination."""
    stmt = select(Problem).join(Pattern).options(
        joinedload(Problem.progress), joinedload(Problem.pattern)
    )
    if pattern_slug:
        stmt = stmt.where(Pattern.slug == pattern_slug)
    if difficulty:
        stmt = stmt.where(Problem.difficulty == difficulty)
    stage_enum = parse_stage(stage)
    if stage_enum:
        stmt = stmt.where(Pattern.stage == stage_enum)
    if tag:
        stmt = stmt.where(Problem.tags.ilike(f"%{tag}%"))
    if q:
        stmt = stmt.where(Problem.name.ilike(f"%{q}%"))

    if status:
        # Status lives on Progress; use an EXISTS-style join to keep counts correct.
        stmt = stmt.outerjoin(Problem.progress)
        if status == Status.NOT_STARTED.value:
            stmt = stmt.where(
                (Progress.status == Status.NOT_STARTED) | (Progress.id.is_(None))
            )
        else:
            stmt = stmt.where(Progress.status == status)

    if sort == "difficulty":
        stmt = stmt.order_by(
            case(
                (Problem.difficulty == Difficulty.EASY, 0),
                (Problem.difficulty == Difficulty.MEDIUM, 1),
                (Problem.difficulty == Difficulty.HARD, 2),
                else_=3,
            ),
            Pattern.order_index,
            Problem.order_index,
        )
    elif sort == "name":
        stmt = stmt.order_by(Problem.name, Pattern.order_index)
    else:
        stmt = stmt.order_by(Pattern.order_index, Problem.order_index)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
    items = list(db.execute(stmt).unique().scalars().all())
    return items, total


def list_problems(
    db: Session,
    pattern_slug: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> list[Problem]:
    """Backward-compatible helper used by the existing HTML routes."""
    items, _ = query_problems(
        db, pattern_slug=pattern_slug, difficulty=difficulty, status=status, q=q
    )
    return items


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


def _due_label(due_at: datetime, now: datetime) -> str:
    days = (now.date() - due_at.date()).days
    if days <= 0:
        return "Due today"
    if days == 1:
        return "1 day ago"
    return f"{days} days ago"


def pattern_stats(
    pattern: Pattern, problems: list[Problem], now: datetime | None = None
) -> dict:
    """Aggregate progress and per-problem state for one pattern."""
    now = now or datetime.utcnow()
    total = len(problems)
    solved = sum(1 for p in problems if p.progress and p.progress.status == Status.SOLVED)
    attempted = sum(
        1 for p in problems if p.progress and p.progress.status == Status.ATTEMPTED
    )
    next_review = min(
        (
            p.progress.next_review_at
            for p in problems
            if p.progress
            and p.progress.status == Status.SOLVED
            and p.progress.next_review_at is not None
        ),
        default=None,
    )
    if next_review is None:
        next_review_label = None
    elif next_review <= now:
        next_review_label = "Due now"
    else:
        next_review_label = next_review.strftime("%b %d")

    due_count = sum(
        1
        for p in problems
        if p.progress
        and p.progress.status == Status.SOLVED
        and p.progress.next_review_at is not None
        and p.progress.next_review_at <= now
    )

    return {
        "slug": pattern.slug,
        "name": pattern.name,
        "stage": pattern.stage.value,
        "order_index": pattern.order_index,
        "short_description": pattern.short_description,
        "total": total,
        "solved": solved,
        "attempted": attempted,
        "not_started": total - solved - attempted,
        "percent_solved": round((solved / total) * 100, 1) if total else 0.0,
        "due_count": due_count,
        "next_review_at": next_review,
        "next_review_label": next_review_label,
        "problems": [
            {
                "id": p.id,
                "name": p.name,
                "difficulty": p.difficulty.value,
                "leetcode_url": p.leetcode_url,
                "status": p.progress.status.value
                if p.progress
                else Status.NOT_STARTED.value,
                "due": bool(
                    p.progress
                    and p.progress.status == Status.SOLVED
                    and p.progress.next_review_at is not None
                    and p.progress.next_review_at <= now
                ),
                "next_review_at": p.progress.next_review_at if p.progress else None,
            }
            for p in problems
        ],
    }


def get_dashboard_data(db: Session):
    patterns = get_patterns(db)
    all_problems = list_problems(db)
    now = datetime.utcnow()

    problems_by_pattern: dict[int, list[Problem]] = {}
    for problem in all_problems:
        problems_by_pattern.setdefault(problem.pattern_id, []).append(problem)

    curriculum = [
        pattern_stats(pattern, problems_by_pattern.get(pattern.id, []), now)
        for pattern in patterns
    ]

    total = len(all_problems)
    solved = sum(1 for p in all_problems if p.progress and p.progress.status == Status.SOLVED)
    attempted = sum(1 for p in all_problems if p.progress and p.progress.status == Status.ATTEMPTED)

    due_problems = []
    for p in all_problems:
        if (
            p.progress
            and p.progress.status == Status.SOLVED
            and p.progress.next_review_at is not None
            and p.progress.next_review_at <= now
        ):
            due_problems.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "pattern_slug": p.pattern.slug,
                    "pattern_name": p.pattern.name,
                    "next_review_at": p.progress.next_review_at,
                    "due_label": _due_label(p.progress.next_review_at, now),
                }
            )
    due_problems.sort(key=lambda item: item["next_review_at"])

    by_pattern = [
        {
            key: item[key]
            for key in (
                "slug",
                "name",
                "stage",
                "total",
                "solved",
                "attempted",
                "not_started",
                "percent_solved",
            )
        }
        for item in curriculum
    ]

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

    by_stage = []
    for stage in Stage:
        stage_patterns = [item for item in curriculum if item["stage"] == stage.value]
        stage_total = sum(item["total"] for item in stage_patterns)
        stage_solved = sum(item["solved"] for item in stage_patterns)
        stage_attempted = sum(item["attempted"] for item in stage_patterns)
        by_stage.append(
            {
                "stage": stage,
                "total": stage_total,
                "solved": stage_solved,
                "attempted": stage_attempted,
                "percent_solved": round((stage_solved / stage_total) * 100, 1)
                if stage_total
                else 0.0,
            }
        )

    activity_counts: dict = {}
    for p in all_problems:
        if p.progress and p.progress.solved_at:
            day = p.progress.solved_at.date().isoformat()
            activity_counts[day] = activity_counts.get(day, 0) + 1
    activity = [
        {"date": day, "count": activity_counts[day]}
        for day in sorted(activity_counts, reverse=True)[:84]
    ]

    return {
        "total_problems": total,
        "total_solved": solved,
        "total_attempted": attempted,
        "percent_solved": round((solved / total) * 100, 1) if total else 0.0,
        "current_streak_days": streak,
        "due_for_review": len(due_problems),
        "by_pattern": by_pattern,
        "by_stage": by_stage,
        "by_difficulty": by_difficulty,
        "activity": activity,
        "curriculum": curriculum,
        "due_problems": due_problems,
    }
