# Procurement Simulator (Proc-Plat)

Teaching lab for client/vendor procurement workflows: student groups draft and publish RFPs for assigned lab lots, other groups bid, clients evaluate and select winners. Admins manage catalog, approvals, imports, and settings.

## Roles & workflow

1. **Students** form groups (size range configured by admin).
2. **Admin** one-click approves a pending group → system auto-assigns the next **2 exclusive** unassigned lots (fails if fewer than 2 free lots).
3. **Client** (owning group) saves RFP drafts, then **submits** → RFP is immediately visible in the vendor gallery and becomes immutable.
4. **Vendors** bid with a PDF; bids always go to the **lot-owning group** only.
5. **Client** scores bids and selects a winner per lot.

CSV import can create groups that are **auto-approved** and lot-assigned in one step.

## Project layout

```text
├── App/
│   ├── controllers/     # Business logic + seed (initialize.py)
│   ├── models/          # SQLAlchemy models
│   ├── views/           # Blueprints (admin, student, auth, …)
│   ├── templates/       # Jinja (admin/, student/)
│   ├── static/          # app.css
│   └── academic_years.py
├── docker/entrypoint.sh
├── docker-compose.yml
├── Dockerfile
├── wsgi.py              # App factory + Flask CLI (flask init)
├── gunicorn_config.py
├── requirements.txt
└── requirements-dev.txt
```

## Quick start (local)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
flask init          # seed DB (CLI only)
flask run
```

Set `SECRET_KEY` in the environment for any non-local deploy.

## Lab demo accounts (classroom only)

These passwords are for local/lab demos. Do not reuse in production.

| Role | Username | Password |
|------|----------|----------|
| Admin | bob | bobpass |
| Student (NexoraTech) | 20240001 | aidenpass |
| Student (unassigned) | 20240031 | darrenpass |

Seed creates exclusive lots and approved groups. See `App/controllers/initialize.py` for the full roster.

## Admin: group size & CSV import

- **Settings** (`/admin/settings`): configure `group_size_min` / `group_size_max`.
- **Import Groups** (`/admin/import-groups`): upload CSV with headers:

```text
student_id,name,email,group_name
20249901,Ada Lovelace,ada@lab.local,AdaForce
20249902,Alan Turing,alan@lab.local,AdaForce
20249903,Grace Hopper,grace@lab.local,AdaForce
```

Rules:

- Login username = `student_id`.
- Group sizes must fall in the configured range.
- Import is transactional; needs `2 × number_of_groups` free lots.
- Success downloads `import_credentials.csv` with temporary passwords.

## Config

Config loads from `App/default_config.py` or `App/custom_config.py`, overridable with `FLASK_`-prefixed env vars.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Session / JWT signing (required in production) |
| `DATABASE_URL` or `SQLALCHEMY_DATABASE_URI` | Postgres / SQLite URI |
| `ENV` | `production` or `development` (cookie security) |
| `CORS_ORIGINS` | Optional comma-separated origins |
| `PORT` | Listen port (default `8080`) |
| `WEB_CONCURRENCY` | Gunicorn workers (default `2`) |

Health check: `GET /health`

## Deploy on EasyPanel

### Option A — Compose (recommended)

1. Create a **Compose** service from this repo.
2. Compose file: `docker-compose.yml` (build path `/`).
3. In **Environment**, paste values from `.env.example` and set strong `SECRET_KEY` + `POSTGRES_PASSWORD`.
4. Enable **Create .env file** so Compose can interpolate secrets.
5. Deploy, then map a domain to service **`web`** on port **`8080`**.
6. Seed demo data once (optional):

```bash
# EasyPanel → web service → Terminal / Exec
flask init
```

`flask init` **resets** the database — only run on a fresh deploy.

### Option B — App + managed Postgres

1. Create a **Postgres** service in the same EasyPanel project.
2. Create an **App** service from this repo; builder = **Dockerfile**.
3. Set environment:

```env
ENV=production
SECRET_KEY=...
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DB
PORT=8080
WEB_CONCURRENCY=2
```

Use EasyPanel’s internal hostname for `HOST` (same project network).
4. Domain → port **8080**. Health path `/health`.

### Local Docker smoke test

```bash
cp .env.example .env
# edit SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
curl http://localhost:8080/health
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## UML

<img width="3666" height="3036" alt="Procurement Simulator Class Diagram" src="https://github.com/user-attachments/assets/8272071a-363a-43ed-b5a4-d95526ef5db9" />
