from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/problems", tags=["progress"])


@router.put("/{problem_id}/progress", response_model=schemas.ProgressOut)
def update_progress(problem_id: int, payload: schemas.ProgressUpdate, db: Session = Depends(get_db)):
    problem = crud.get_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return crud.update_progress(db, problem, new_status=payload.status, notes=payload.notes)


@router.post("/{problem_id}/review", response_model=schemas.ProgressOut)
def review_again(problem_id: int, db: Session = Depends(get_db)):
    problem = crud.get_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    if problem.progress is None or problem.progress.status.value != "solved":
        raise HTTPException(status_code=400, detail="Problem must be solved before it can be reviewed")
    return crud.review_problem_again(db, problem)
