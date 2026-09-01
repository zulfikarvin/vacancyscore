# VacancyScore

VacancyScore compares a vacancy with a user's stored CVs, recommends the
strongest match, explains gaps, and exports the analysis as PDF.

## Free deployment architecture

The production stack is designed to fit free tiers for a portfolio/demo:

```text
Browser
  |
  v
Vercel project 1: Next.js frontend
  |  same-origin /api proxy
  v
Vercel project 2: FastAPI Python functions
  |---- Supabase Auth
  |---- Supabase Postgres
  `---- Gemini API (analysis + embeddings)
```

Both Vercel projects use this same GitHub repository. They are separate projects
because Vercel gives each project one root directory and one framework/runtime:
the frontend root is `frontend`, while the backend root is `backend`.

The backend does not download a machine-learning model. CV and vacancy vectors
come from `gemini-embedding-001` through a small HTTP request. This removes
PyTorch, Sentence Transformers, NumPy, Hugging Face model files, and the
LangChain community loader package from the deployed function.

This can run at no cost while usage remains within Vercel Hobby, Supabase Free,
and Gemini API free-tier quotas. Free plans have usage and inactivity limits, so
this architecture is intended for a portfolio or low-traffic demo.

## Project structure

```text
backend/
  app/main.py         FastAPI routes
  app/auth.py         Supabase Auth and HTTP-only cookies
  app/chains.py       Gemini/LangChain analysis pipeline
  app/embeddings.py   Gemini embeddings and cosine ranking
  app/store.py        Supabase Postgres access through SQLAlchemy
  app/parsing.py      Lightweight PDF/DOCX extraction
  app/pdf_report.py   Downloadable analysis report
  check_database.py   Create/update database tables
  reembed_cvs.py      Upgrade stored CV vectors
frontend/
  app/                Next.js pages
  components/         User interface
  lib/api.ts          Typed API client
```

SQLAlchemy remains because it is the small Python database layer, not a database
service. Supabase provides PostgreSQL; SQLAlchemy safely maps Python objects and
queries to that database. It does not add another paid service.

## Run locally

Requirements: Python 3.12, Node.js 20+, and
[uv](https://docs.astral.sh/uv/).

Backend:

```bash
cd backend
cp .env.example .env
uv venv
uv pip install -r pyproject.toml
uv run python check_database.py
uv run uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend automatically uses the backend at
`http://localhost:8000` during development.

Run checks:

```bash
cd backend
uv run pytest

cd ../frontend
npm run build
```

## Environment variables

Backend variables:

| Variable | Purpose |
| --- | --- |
| `GOOGLE_API_KEY` | Gemini analysis and embedding API key |
| `GEMINI_MODEL` | Main structured-analysis model |
| `GEMINI_EXTRACTION_MODEL` | Vacancy requirement extraction model |
| `EMBEDDING_MODEL` | Defaults to `gemini-embedding-001` |
| `DATABASE_URL` | Supabase transaction-pooler connection string |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (name retained for compatibility) |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable/anon key |
| `ALLOWED_ORIGINS` | Comma-separated trusted frontend URLs |
| `PUBLIC_APP_URL` | Frontend URL used for password recovery |
| `ENVIRONMENT` | Set to `production` on Vercel |
| `USE_MOCK_LLM` | `false` for real Gemini calls; `true` for offline fixtures |

Frontend production variable:

| Variable | Purpose |
| --- | --- |
| `BACKEND_API_URL` | Backend Vercel URL, for example `https://vacancyscore-api.vercel.app` |

`BACKEND_API_URL` is server-only. Next.js proxies browser requests from
`/api/*` to FastAPI, which keeps authentication cookies first-party.

## Deploy both projects to Vercel

Before deployment, initialize the Supabase tables once from your computer:

```bash
cd backend
uv run python check_database.py
```

### 1. Deploy the backend

1. In Vercel, select **Add New > Project** and import this GitHub repository.
2. Name it something like `vacancyscore-api`.
3. Set **Root Directory** to `backend`.
4. Add all backend variables listed above. Use:
   - `ENVIRONMENT=production`
   - `USE_MOCK_LLM=false`
   - `ALLOWED_ORIGINS=http://localhost:3000` temporarily
   - `PUBLIC_APP_URL=http://localhost:3000` temporarily
5. Deploy and copy the generated backend URL.
6. Open `https://YOUR-BACKEND.vercel.app/health` and confirm the response says
   `"status":"ok"`.

Vercel recognizes `app/main.py` as FastAPI; `backend/pyproject.toml` also
declares `app.main:app` explicitly.

### 2. Deploy the frontend

1. In Vercel, create another project from the same GitHub repository.
2. Name it `vacancyscore`.
3. Set **Root Directory** to `frontend`.
4. Add `BACKEND_API_URL=https://YOUR-BACKEND.vercel.app` without a trailing
   slash.
5. Deploy and copy the frontend URL.

### 3. Connect the final URLs

Return to the backend project's environment variables and set:

```env
ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app,http://localhost:3000
PUBLIC_APP_URL=https://YOUR-FRONTEND.vercel.app
```

Redeploy the backend after changing those values.

In Supabase, open **Authentication > URL Configuration**:

- Set **Site URL** to `https://YOUR-FRONTEND.vercel.app`.
- Add `https://YOUR-FRONTEND.vercel.app/reset-password` to Redirect URLs.
- Keep `http://localhost:3000/reset-password` for local development.

Then test signup, login, CV upload, analysis, PDF download, logout, and password
recovery from the deployed frontend.

## Existing CV migration

Older CV rows may contain 384-dimensional local Hugging Face vectors. The
application records the current embedding version and automatically regenerates
an old vector before the next analysis. To upgrade all rows immediately:

```bash
cd backend
uv run python reembed_cvs.py
```

This command calls Gemini once per stored CV, so run it only after confirming
`GOOGLE_API_KEY` and `USE_MOCK_LLM=false`.

## Key design choices

- No vector database: each user has at most ten CVs, so direct cosine ranking is
  simpler and cheaper.
- No local ML model: Gemini embeddings keep Vercel's Python function small.
- LangChain stays only for the structured analysis chain; it is not used for
  parsing or embeddings.
- Supabase owns authentication and PostgreSQL; Vercel owns application runtime.
- On Vercel, SQLAlchemy uses no local connection pool because Supabase's
  transaction pooler already manages connections.
