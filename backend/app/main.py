from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
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
    # Idempotent: safe to re-run every start, keeps DB in sync with the seed JSON
    # without ever touching user progress data.
    load_seed()


@app.get("/")
def root():
    return RedirectResponse(url="/patterns")


@app.get("/patterns")
def patterns_list(request: Request, db: Session = Depends(get_db)):
    dashboard = crud.get_dashboard_data(db)
    stats_by_slug = {s["slug"]: s for s in dashboard["by_pattern"]}
    patterns = crud.get_patterns(db)
    return templates.TemplateResponse(
        request,
        "patterns_list.html",
        {"patterns": patterns, "stats_by_slug": stats_by_slug},
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
    return templates.TemplateResponse(
        request,
        "pattern_detail.html",
        {
            "pattern": pattern,
            "problems": problems,
            "filters": {"difficulty": difficulty or "", "status": status or "", "q": q or ""},
        },
    )


@app.get("/dashboard")
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    data = crud.get_dashboard_data(db)
    return templates.TemplateResponse(request, "dashboard.html", {"data": data})
