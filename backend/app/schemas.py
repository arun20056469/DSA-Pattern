from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Difficulty, Status


class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Status
    notes: str
    review_count: int
    last_reviewed_at: datetime | None
    next_review_at: datetime | None
    solved_at: datetime | None


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pattern_id: int
    slug: str
    name: str
    difficulty: Difficulty
    leetcode_url: str
    hint: str
    order_index: int
    progress: ProgressOut | None = None


class PatternOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    order_index: int
    short_description: str
    when_to_use: str
    recognition_tips: str
    complexity: str
    template_code: str


class PatternWithProblems(PatternOut):
    problems: list[ProblemOut] = []


class ProgressUpdate(BaseModel):
    status: Status | None = None
    notes: str | None = None


class PatternStats(BaseModel):
    slug: str
    name: str
    total: int
    solved: int
    attempted: int
    not_started: int
    percent_solved: float


class DashboardOut(BaseModel):
    total_problems: int
    total_solved: int
    total_attempted: int
    percent_solved: float
    current_streak_days: int
    due_for_review: int
    by_pattern: list[PatternStats]
    by_difficulty: dict[str, dict[str, int]]
