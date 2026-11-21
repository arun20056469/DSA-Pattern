from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.db_migrations import run_migrations, stamp_fresh_head
from app.routers import api_dashboard, api_patterns, api_problems, api_progress
from app.seed_loader import load_seed

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="DSA Patterns Platform")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(api_patterns.router)
app.include_router(api_problems.router)
app.include_router(api_progress.router)
app.include_router(api_dashboard.router)


@app.on_event("startup")
def on_startup():
    # Bring legacy databases onto the current schema first, preserving progress.
    fresh = not run_migrations()
    # Idempotent: safe to re-run every start, keeps DB in sync with the seed JSON
    # without ever touching user progress data.
    load_seed()
    if fresh:
        stamp_fresh_head()


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/patterns")
def patterns_list(
    request: Request, stage: str | None = None, db: Session = Depends(get_db)
):
    data = crud.get_dashboard_data(db)
    active = crud.parse_stage(stage)
    curriculum = [
        item
        for item in data["curriculum"]
        if active is None or item["stage"] == active.value
    ]
    return templates.TemplateResponse(
        request,
        "patterns_list.html",
        {"curriculum": curriculum, "active_stage": active.value if active else ""},
    )


@app.get("/patterns/{slug}")
def pattern_detail(
    request: Request,
    slug: str,
    difficulty: str | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    pattern = crud.get_pattern_by_slug(db, slug)
    if pattern is None:
        return templates.TemplateResponse(
            request, "not_found.html", {"slug": slug}, status_code=404
        )
    problems = crud.list_problems(db, pattern_slug=slug, difficulty=difficulty, status=status, q=q)
    stats = crud.pattern_stats(pattern, pattern.problems)
    all_patterns = crud.get_patterns(db)
    index = next((i for i, p in enumerate(all_patterns) if p.slug == slug), -1)
    return templates.TemplateResponse(
        request,
        "pattern_detail.html",
        {
            "pattern": pattern,
            "problems": problems,
            "stats": stats,
            "previous": all_patterns[index - 1] if index > 0 else None,
            "next": all_patterns[index + 1] if 0 <= index < len(all_patterns) - 1 else None,
            "filters": {"difficulty": difficulty or "", "status": status or "", "q": q or ""},
        },
    )


@app.get("/dashboard")
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    data = crud.get_dashboard_data(db)
    return templates.TemplateResponse(request, "dashboard.html", {"data": data})


@app.get("/problems")
def problems_library(
    request: Request,
    pattern: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    q: str | None = None,
    stage: str | None = None,
    tag: str | None = None,
    sort: str = "order",
    page: int = 1,
    db: Session = Depends(get_db),
):
    page = max(1, page)
    limit = 25
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
        offset=(page - 1) * limit,
    )
    return templates.TemplateResponse(
        request,
        "problems_library.html",
        {
            "items": items,
            "patterns": crud.get_patterns(db),
            "total": total,
            "page": page,
            "pages": max(1, (total + limit - 1) // limit),
            "filters": {
                "pattern": pattern or "",
                "difficulty": difficulty or "",
                "status": status or "",
                "q": q or "",
                "stage": stage or "",
                "tag": tag or "",
                "sort": sort,
            },
        },
    )


@app.get("/review")
def review_page(request: Request, db: Session = Depends(get_db)):
    data = crud.get_dashboard_data(db)
    return templates.TemplateResponse(
        request, "review.html", {"due_problems": data["due_problems"]}
    )
