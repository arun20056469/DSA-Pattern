from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Difficulty, Stage, Status


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
    leetcode_id: int | None = None
    leetcode_slug: str | None = None
    tags: str | None = None
    hint: str
    order_index: int
    progress: ProgressOut | None = None


class ProblemPage(BaseModel):
    items: list[ProblemOut]
    total: int
    limit: int
    offset: int


class PatternOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    stage: Stage
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
    stage: Stage
    total: int
    solved: int
    attempted: int
    not_started: int
    percent_solved: float


class CurriculumProblem(BaseModel):
    id: int
    name: str
    difficulty: Difficulty
    leetcode_url: str
    status: Status
    due: bool
    next_review_at: datetime | None = None


class CurriculumPattern(BaseModel):
    slug: str
    name: str
    stage: Stage
    order_index: int
    short_description: str
    total: int
    solved: int
    attempted: int
    not_started: int
    percent_solved: float
    due_count: int
    next_review_at: datetime | None = None
    next_review_label: str | None = None
    problems: list[CurriculumProblem]


class DueProblem(BaseModel):
    id: int
    name: str
    pattern_slug: str
    pattern_name: str
    next_review_at: datetime
    due_label: str


class StageStat(BaseModel):
    stage: Stage
    total: int
    solved: int
    attempted: int
    percent_solved: float


class ActivityDay(BaseModel):
    date: str
    count: int


class DashboardOut(BaseModel):
    total_problems: int
    total_solved: int
    total_attempted: int
    percent_solved: float
    current_streak_days: int
    due_for_review: int
    by_pattern: list[PatternStats]
    by_stage: list[StageStat]
    by_difficulty: dict[str, dict[str, int]]
    activity: list[ActivityDay]
    curriculum: list[CurriculumPattern]
    due_problems: list[DueProblem]
