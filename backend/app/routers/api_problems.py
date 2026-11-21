from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get("", response_model=list[schemas.ProblemOut])
def list_problems(
    pattern: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    q: str | None = None,
    stage: str | None = None,
    tag: str | None = None,
    db: Session = Depends(get_db),
):
    items, _ = crud.query_problems(
        db,
        pattern_slug=pattern,
        difficulty=difficulty,
        status=status,
        q=q,
        stage=stage,
        tag=tag,
    )
    return items


@router.get("/search", response_model=schemas.ProblemPage)
def search_problems(
    pattern: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    q: str | None = None,
    stage: str | None = None,
    tag: str | None = None,
    sort: str = "order",
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    items, total = crud.query_problems(
        db,
        pattern_slug=pattern,
        difficulty=difficulty,
        status=status,
        q=q,
        stage=stage,
        tag=tag,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{problem_id}", response_model=schemas.ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = crud.get_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem
