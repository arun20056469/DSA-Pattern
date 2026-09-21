from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("", response_model=list[schemas.PatternOut])
def list_patterns(db: Session = Depends(get_db)):
    return crud.get_patterns(db)


@router.get("/{slug}", response_model=schemas.PatternWithProblems)
def get_pattern(slug: str, db: Session = Depends(get_db)):
    pattern = crud.get_pattern_by_slug(db, slug)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern
