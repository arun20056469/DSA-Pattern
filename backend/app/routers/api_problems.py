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
    db: Session = Depends(get_db),
):
    return crud.list_problems(db, pattern_slug=pattern, difficulty=difficulty, status=status, q=q)


@router.get("/{problem_id}", response_model=schemas.ProblemOut)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = crud.get_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem
