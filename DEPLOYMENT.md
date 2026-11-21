# Deploying DSA Patterns

The app is a FastAPI + SQLAlchemy + SQLite + Jinja2 service. On every startup it:

1. runs Alembic migrations against the configured SQLite file,
2. idempotently seeds 21 patterns / 420 problems from `patterns_seed.json`,
3. leaves your progress/notes untouched.

Because progress lives in SQLite, **the database must be on a persistent volume**. The container defaults to `DSA_DB_PATH=/data/dsa.db`, and all deployment configs mount a volume at `/data`.

> Render free web services have an ephemeral filesystem. Use a paid **Starter** service (as in `render.yaml`) or switch to a hosted database if you need free-tier persistence.

---

## Option A — Render (Blueprint)

Your repo already contains a Render blueprint from the initial commit. I kept the
existing service name (`dsa-pattern`) and native Python runtime, and only added
the persistent disk plus `DSA_DB_PATH`.

1. Push this repo to GitHub (already done).
2. In Render, choose **New → Blueprint**.
3. Connect the `DSA-Pattern` repository. Render detects `render.yaml`.
4. Confirm the service:
   - **Name:** `dsa-pattern`
   - **Runtime:** Python, `rootDir: backend`
   - **Plan:** Starter (required — free services have no persistent disk)
   - **Disk:** `dsa-data`, mount path `/data`, 1 GB
   - **Env:** `DSA_DB_PATH=/data/dsa.db`
5. Click **Apply**. If you already had a free Render service, Render may create a
   new one because the plan/disk changed — delete the old free service afterward
   to avoid confusion.
6. First boot seeds the DB automatically. Open
   `https://dsa-pattern.onrender.com/dashboard`.

Blueprint file: [`render.yaml`](render.yaml)

---

## Option B — Railway

1. Create a **New Project → Deploy from GitHub repo** and select `DSA-Pattern`.
2. Railway detects `backend/Dockerfile` via `railway.json`.
3. Add a **Persistent Volume** to the service:
   - **Mount path:** `/data`
   - **Size:** 1 GB
4. Add a variable: `DSA_DB_PATH=/data/dsa.db`
5. Generate a domain under **Settings → Networking**.
6. Open `https://<your-domain>/dashboard`.

Config file: [`railway.json`](railway.json)

---

## Local Docker test

```bash
cd backend
docker build -t dsa-patterns .
docker run --rm -p 8000:8000 -v dsa-data:/data dsa-patterns
```

Then open http://localhost:8000/dashboard.

To start completely fresh, remove the named volume:

```bash
docker volume rm dsa-data
```

---

## Useful checks

| Path | Purpose |
|---|---|
| `/dashboard` | Health check / overview |
| `/patterns` | Curriculum |
| `/problems` | Global library |
| `/review` | Review queue |
| `/docs` | Swagger API docs |

Verify the configured DB path and seeding before deploying:

```bash
cd backend
set DSA_DB_PATH=/data/dsa.db
python scripts/deploy_check.py
```

On Windows PowerShell:

```powershell
$env:DSA_DB_PATH = "/data/dsa.db"
python scripts/deploy_check.py
```

---

## Notes

- Do **not** commit `data/dsa.db` or backups. The seed JSON is the source of truth; the volume holds only user progress.
- Back up the `/data` volume before changing the schema or reseeding.
- If you later run multiple instances, SQLite is no longer sufficient — migrate to Postgres and set a standard `DATABASE_URL`.
