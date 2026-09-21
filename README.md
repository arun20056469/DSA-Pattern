# DSA Patterns Platform

A pattern-first alternative to a flat LeetCode-style problem list. Instead of browsing
one giant problem list, you browse by **pattern** (Two Pointers, Sliding Window,
Binary Search, ...), read a short explanation + template for the pattern, then work
through a curated, difficulty-ordered problem list for it — tracking solved/attempted
status, notes, and spaced-repetition review dates as you go.

## Stack & why

- **Backend: FastAPI** (over Flask) — Pydantic request/response validation, automatic
  OpenAPI docs at `/docs`, native async, and it serves Jinja2 HTML templates exactly
  as easily as Flask does, so one codebase gives you both the JSON API and the web UI.
- **DB: SQLite via SQLAlchemy 2.0 ORM** — zero setup, a single file at `data/dsa.db`,
  trivially swappable for Postgres later (only `database.py` would change).
- **Frontend: server-rendered Jinja2 templates + vanilla JS** (`fetch` calls to the
  JSON API for marking progress/notes without a full page reload). No build step,
  no npm — open the browser and it works. A React frontend is straightforward to add
  later since the backend already exposes a full JSON API under `/api/*`, completely
  decoupled from the HTML routes.
- Single-user, no auth — this is a personal tracker. Multi-user would mean adding a
  `users` table and scoping `Progress` rows by `user_id`.

## Project structure

```
DSA/
  backend/
    requirements.txt
    app/
      main.py              # FastAPI app: HTML routes + router wiring + startup seed
      database.py          # SQLAlchemy engine/session, resolves data/dsa.db
      models.py            # Pattern, Problem, Progress ORM models
      schemas.py           # Pydantic request/response models
      crud.py              # DB queries + spaced-repetition + dashboard aggregation
      seed_loader.py        # idempotent JSON -> DB loader (runs on every startup)
      import_csv.py          # CLI to bulk-import extra problems from a CSV
      routers/
        api_patterns.py     # GET /api/patterns, /api/patterns/{slug}
        api_problems.py     # GET /api/problems (filterable), /api/problems/{id}
        api_progress.py     # PUT .../progress, POST .../review
        api_dashboard.py    # GET /api/dashboard
      seed/
        patterns_seed.json  # all 15 patterns; 5 fully populated with 10 problems each
        sample_import.csv   # example file for the CSV importer
      templates/            # Jinja2 HTML templates
      static/                # CSS + vanilla JS
  data/
    dsa.db                 # created automatically on first run
  README.md
```

## Data model

- **Pattern** — slug, name, order, `short_description`, `when_to_use`,
  `recognition_tips`, `complexity`, `template_code` (canonical Python snippet).
- **Problem** — belongs to a Pattern; name, difficulty (Easy/Medium/Hard), direct
  LeetCode URL, one-line hint, order within the pattern.
- **Progress** — one row per Problem (created on first status change); status
  (`not_started` / `attempted` / `solved`), free-text notes, `review_count`,
  `last_reviewed_at`, `next_review_at`, `solved_at`.

## Patterns seeded

**21 patterns, 210 problems total** — every pattern is fully populated with 10 real
LeetCode problems each, ordered easy → medium → hard, each with a direct URL and a
one-line hint. The pattern order on `/patterns` is deliberately a low-level →
advanced learning path, not alphabetical:

| # | Pattern | # | Pattern |
|---|---------|---|---------|
| 1 | Arrays & Hashing *(foundations)* | 12 | Backtracking |
| 2 | Two Pointers | 13 | Union-Find (Disjoint Set) |
| 3 | Sliding Window | 14 | Graphs — Advanced (shortest path, topo sort) |
| 4 | Stacks & Queues (Fundamentals) | 15 | Heaps / Top-K |
| 5 | Linked List (Fundamentals) | 16 | Greedy |
| 6 | Fast & Slow Pointers | 17 | Bit Manipulation |
| 7 | Binary Search (and variants) | 18 | Dynamic Programming (1D) |
| 8 | Merge Intervals | 19 | Dynamic Programming (2D / Knapsack) |
| 9 | Monotonic Stack/Queue | 20 | Math & Number Theory |
| 10 | Trie (Prefix Tree) | 21 | Design / Advanced Data Structures |
| 11 | DFS/BFS (Trees & Graphs) | | |

Patterns 1, 4, 5, 20, and 21 (Arrays & Hashing, Stacks & Queues Fundamentals,
Linked List Fundamentals, Math & Number Theory, Design / Advanced Data Structures)
were added beyond your original 14-pattern list to round out a genuine beginner →
advanced curriculum: fundamentals come first, dependency/shortest-path graph
algorithms and system-design-style "build a data structure" problems close it out.

## Setup & running locally

Requires Python 3.11+ (tested on 3.14).

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/patterns**. The SQLite DB (`data/dsa.db`) and all
15 patterns / 50 problems are created automatically on first startup — no manual
migration step. The seed loader is idempotent and re-runs on every startup, so
editing `patterns_seed.json` and restarting the server picks up the changes
without ever touching your saved progress/notes.

API docs (Swagger UI): **http://127.0.0.1:8000/docs**

### Adding more problems

Either:
- Edit `backend/app/seed/patterns_seed.json` directly and restart the server, or
- Bulk-import from CSV (adds new problems, updates existing ones by slug, and can
  even create brand-new patterns on the fly):

```bash
python -m app.import_csv app/seed/sample_import.csv
```

CSV columns: `pattern_slug, pattern_name, name, slug, difficulty, leetcode_url, hint, order`
(`pattern_name` only required if `pattern_slug` doesn't exist yet; `slug` and `order`
are optional and auto-generated/appended if omitted).

## Using it

- **`/patterns`** — grid of all patterns with a solved/total badge and progress bar.
- **`/patterns/{slug}`** — pattern explanation, complexity notes, recognition tips,
  the canonical template snippet, and the problem table. Each row: name (links to
  LeetCode in a new tab), difficulty badge, hint, a status dropdown
  (not started/attempted/solved — saved instantly via `fetch`), and a notes panel.
  Filter by difficulty, status, or free-text search via the query params / form.
- **`/dashboard`** — total solved / overall %, current streak (consecutive days with
  at least one problem solved), count due for spaced-repetition review, breakdown by
  difficulty, and a per-pattern progress table.

## Spaced repetition

Implemented as a simple Leitner-style fixed interval schedule: solving (or
re-reviewing via `POST /api/problems/{id}/review`) a problem schedules its next
review `[1, 3, 7, 16, 35]` days out (indexed by `review_count`, capped at the last
value). The dashboard's "due for review" count sums problems whose `next_review_at`
has passed. This is intentionally simple (not full SM-2 with an ease factor) —
feasible to upgrade later by adding an `ease_factor` column and adjusting the
interval formula in `crud.py`'s `_next_interval_days`.

## Extra features — feasibility notes

- **Spaced repetition reminders** — implemented (see above). A real "reminder"
  (email/notification) would need a scheduler (e.g. APScheduler) checking
  `next_review_at <= now` and an email/notification integration — straightforward
  to add as a background job since the data is already tracked.
- **Difficulty/status filtering & search** — implemented on the pattern detail page
  and via `GET /api/problems?pattern=&difficulty=&status=&q=`.
- **Notes/solution approach per problem** — implemented (`Progress.notes`, editable
  inline per problem).
- **CSV/JSON import** — implemented (`import_csv.py` for CSV; `seed_loader.py` +
  editing the seed JSON directly for bulk JSON changes). A file-upload UI for CSV
  import would be a small addition (`python-multipart` is already a dependency).

## Known simplifications

- Single user, no authentication.
- `on_event("startup")` is used for the seed hook; FastAPI's newer `lifespan`
  context-manager API is a drop-in equivalent if you prefer that style later.
