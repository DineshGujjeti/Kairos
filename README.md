# Kairos

**A Multi-Agent Enterprise Decision Intelligence Platform for Supply Chain & Inventory Analytics.**

Kairos turns raw supply chain and inventory data into explainable,
evidence-based business decisions — going beyond dashboards to answer
*what happened, why it happened, what's likely next, what to do about
it, and what happens if you do something different.*

Full architecture, feature rationale, and module roadmap: [`docs/architecture.md`](docs/architecture.md) *(the Phase 0 analysis — add the file here if not already present)*.
Non-obvious engineering decisions: [`docs/adr/`](docs/adr/).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL (transactional) + DuckDB (analytical) |
| ML | Scikit-learn, LightGBM, XGBoost, Prophet (baseline) |
| Explainability | SHAP |
| AI Assistant | LangGraph + Llama 3 / Qwen |
| Deployment | Docker, Docker Compose |

---

## Getting Started (Docker — recommended)

```bash
cp backend/.env.example backend/.env
# edit backend/.env: set SECRET_KEY and POSTGRES_PASSWORD at minimum

docker compose up --build
```

- Backend: http://localhost:8000/api/v1/docs (Swagger UI)
- Frontend: http://localhost:5173
- Health check: http://localhost:8000/health

## Getting Started (local, without Docker)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit as needed; point POSTGRES_SERVER at a local Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

**Tests**

```bash
cd backend
pytest
```

---

## Repository Structure

```
kairos/
├── backend/     FastAPI app, ML services, Alembic migrations, tests
├── frontend/    React + TypeScript SPA
├── docs/        Architecture docs and ADRs
└── docker-compose.yml
```

Each backend module lives across three layers, consistently:
`api/v1/<module>/routes.py` (thin HTTP layer) → `services/<module>_service.py`
(business logic) → `db/models/` (persistence). Route handlers never
contain business logic directly — this is what keeps services unit
testable without spinning up the whole HTTP stack.

---

## Git Workflow

- `main` — always deployable. Protected; only merged via reviewed PR.
- `develop` — integration branch; features merge here first.
- `feature/module-N-short-name` — one branch per module (e.g.
  `feature/module-2-ingestion-pipeline`), branched from `develop`.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`. Example:
`feat(auth): add refresh token rotation`.

Each module is merged to `develop` only once its own tests pass and its
section of this README (or a linked doc) is updated — no module is
considered "done" without both.

---

## Coding Standards

**Backend (Python)**
- Formatted with `black`, linted with `ruff`, type-checked with `mypy` (configured in `pyproject.toml`).
- Route handlers stay thin: parse request → call service → return response.
- All config through `app/core/config.py`; never `os.environ.get()` inline.
- All new models registered in `app/db/models/__init__.py` (required for Alembic autogenerate).
- Every service function has a docstring explaining *why*, not just *what*, when the reasoning isn't obvious from the code.

**Frontend (TypeScript)**
- One feature = one folder under `src/features/<name>/` (`api.ts`, `store.ts`, `components/`).
- Shared, reusable primitives (buttons, inputs, cards) live in `src/components/ui/` following the shadcn/ui pattern in `button.tsx`.
- All API calls go through `src/lib/api-client.ts` — never a raw `axios`/`fetch` call scattered in a component, except infra probes like `/health`.
- Strict TypeScript (`strict: true`); no `any` without a comment justifying it.

**Testing**
- Every module ships with tests before being considered complete (see Development Rules in the project brief). Backend tests run against SQLite in-memory for speed; this is intentional (see `tests/conftest.py`) and does not test Postgres-specific behavior — migrations themselves are the source of truth for schema correctness.

---

## Status

- [x] Module 1 — Project Foundation
- [x] Module 2 — Ingestion Pipeline (upload, validation, cleaning)
- [ ] Module 3 — EDA + KPI Engine
- [ ] Module 4 — Demand Forecasting Service
- [ ] Module 5 — Supplier Risk / Delivery Delay Service
- [ ] Module 6 — Explainability Layer (SHAP)
- [ ] Module 7 — Root Cause / Driver Decomposition
- [ ] Module 8 — Recommendation Engine
- [ ] Module 9 — What-If Simulation Engine
- [ ] Module 10 — AI Assistant (LangGraph)
- [ ] Module 11 — PDF Reporting
- [ ] Module 12 — Hardening & Deployment
