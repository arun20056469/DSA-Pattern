import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Difficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class Status(str, enum.Enum):
    NOT_STARTED = "not_started"
    ATTEMPTED = "attempted"
    SOLVED = "solved"


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    short_description: Mapped[str] = mapped_column(Text)
    when_to_use: Mapped[str] = mapped_column(Text)
    recognition_tips: Mapped[str] = mapped_column(Text)
    complexity: Mapped[str] = mapped_column(Text)
    template_code: Mapped[str] = mapped_column(Text)

    problems: Mapped[list["Problem"]] = relationship(
        back_populates="pattern",
        cascade="all, delete-orphan",
        order_by="Problem.order_index",
    )


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("pattern_id", "slug", name="uq_problem_pattern_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern_id: Mapped[int] = mapped_column(ForeignKey("patterns.id"))
    slug: Mapped[str] = mapped_column(String(200), index=True)
    name: Mapped[str] = mapped_column(String(300))
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty))
    leetcode_url: Mapped[str] = mapped_column(String(500))
    hint: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    pattern: Mapped["Pattern"] = relationship(back_populates="problems")
    progress: Mapped["Progress"] = relationship(
        back_populates="problem", uselist=False, cascade="all, delete-orphan"
    )


class Progress(Base):
    __tablename__ = "progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), unique=True)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.NOT_STARTED)
    notes: Mapped[str] = mapped_column(Text, default="")
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    solved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    problem: Mapped["Problem"] = relationship(back_populates="progress")
