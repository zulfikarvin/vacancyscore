# VacancyScore

Paste a job vacancy. VacancyScore picks which of your stored CVs to send, scores
the fit honestly, and tells you the exact edits to make.

It is a small multi-user web app: sign up, upload a few versions of your CV, and
every vacancy you paste comes back with a fit score, matched and missing
keywords, a gap table with a suggested fix per row, and a short checklist of
concrete edits. Every analysis is saved to your history.

![Analysis results](docs/results.png)

---

## Architecture

Two deploys, one contract. The frontend is static on Vercel and talks to a
FastAPI container on Railway over a signed session cookie.

```mermaid
flowchart TB
    subgraph V["Vercel"]
        UI["Next.js 15 App Router<br/>Tailwind · shadcn/ui · Recharts"]
        API["lib/api.ts<br/>typed client, credentials: include"]
        UI --- API
    end

    subgraph R["Railway (Docker)"]
        direction TB
        ROUTES["main.py<br/>routes only"]
        AUTH["auth.py<br/>argon2 · signed cookie"]
        CHAINS["chains.py<br/>LCEL pipeline"]
        EMB["embeddings.py<br/>bge-small-en-v1.5 · numpy cosine"]
        STORE["store.py<br/>SQLAlchemy, user-scoped CRUD"]
        LIMITS["limits.py<br/>quotas"]

        ROUTES --> AUTH
        ROUTES --> LIMITS
        ROUTES --> CHAINS
        ROUTES --> STORE
        CHAINS --> EMB
    end

    PG[("PostgreSQL<br/>users · cvs · analyses")]
    GEM["Gemini 2.5 Flash"]

    API -- "HTTPS + session cookie" --> ROUTES
    STORE --> PG
    CHAINS -- "2 structured calls" --> GEM
```

### The analysis pipeline

```
vacancy text
     │
     ├─▶ 1. rank CVs          embeddings.py   local, CPU, ~10ms
     │      embed the vacancy, cosine-compare against every stored CV
     │      vector, pick the winner and keep all the percentages
     │
     ├─▶ 2. extract requirements    chains.py   small Gemini call
     │      role, company, hard requirements, nice-to-haves, keywords
     │      → ExtractedRequirements
     │
     └─▶ 3. deep analysis           chains.py   main Gemini call
            winning CV + vacancy + extracted requirements
            → VacancyAnalysis (structured output)
```

Steps 2 and 3 are one LCEL chain: `RunnablePassthrough.assign` carries the
extracted requirements from the first structured call into the prompt of the
second, so the whole thing is a single `.invoke()`.

### Repo layout

```
vacancyscore/
  backend/
    app/
      main.py        FastAPI app + routes only
      auth.py        argon2 hashing, signed session cookie, current_user
      chains.py      the LCEL pipeline and every LLM prompt
      schemas.py     Pydantic models -- the single source of truth
      embeddings.py  HF embedder + cosine ranking (pure numpy)
      store.py       SQLAlchemy models + user-scoped CRUD
      parsing.py     PDF/DOCX text extraction
      limits.py      rate limits and quotas
      errors.py      AppError -> typed ErrorResponse
      config.py      pydantic-settings
    tests/
    Dockerfile
    pyproject.toml
  frontend/
    app/             App Router pages: /, /login, /signup
    components/      ui/ (shadcn primitives), sidebar/, results/
    lib/             api.ts, types.ts, markdown.ts, utils.ts
```

---

## Running it locally

You need Python 3.11+, Node 20+, and [uv](https://docs.astral.sh/uv/).

**Backend**

```bash
cd backend
cp .env.example .env          # works as-is: no API key needed, mock LLM on
uv venv && uv pip install -r pyproject.toml
uv run uvicorn app.main:app --reload
```

`GET /health` reports `{"status":"ok","llm":"mock"}` until you set a real
`GOOGLE_API_KEY` and `USE_MOCK_LLM=false`. Interactive API docs are at
`/docs`.

**Frontend**

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

**Tests**

```bash
cd backend
uv run pytest
```

No test ever calls Gemini or downloads a model — see *Decisions* below.

### Environment variables

| Variable | Where | Notes |
| --- | --- | --- |
| `GOOGLE_API_KEY` | backend | Gemini 2.5 Flash. Leave empty to stay on the mock. |
| `SECRET_KEY` | backend | Signs the session cookie. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | backend | SQLite locally, `postgresql+psycopg://...` in production. |
| `ALLOWED_ORIGINS` | backend | Comma-separated. Must include the Vercel URL for the cookie to work. |
| `PUBLIC_APP_URL` | backend | Canonical frontend URL used in password-reset emails. |
| `ENVIRONMENT` | backend | `production` switches the cookie to `SameSite=None; Secure`. |
| `PORT` | backend | Injected by Railway. |
| `ANALYZE_DAILY_LIMIT` | backend | Analyses per user per UTC day. Default 10. |
| `USE_MOCK_LLM` | backend | `true` serves a fixture analysis and a hash-based embedder. |
| `NEXT_PUBLIC_API_URL` | frontend | Base URL of the backend. Never hardcoded anywhere else. |

For password recovery, add these URLs in **Supabase > Authentication > URL Configuration > Redirect URLs**:

```text
http://localhost:3000/reset-password
https://<your-app>.vercel.app/reset-password
```

### Supabase PostgreSQL

VacancyScore can use Supabase as its production database without replacing the
existing authentication or API layer. In Supabase, open **Connect**, select the
**Transaction pooler**, and place its connection string in `backend/.env`:

```env
DATABASE_URL=postgresql://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@POOLER_HOST:6543/postgres?sslmode=require
```

Then initialize and verify the database:

```bash
cd backend
uv run python check_database.py
```

The password must be URL-encoded if it contains characters such as `@`, `:`,
`/`, `#`, or `%`. Keep `.env` private; it is excluded from Git.

---

## Decisions, and why

**numpy instead of a vector database.** Similarity is only ever computed inside
one user account, against at most ten CVs. That is a 10 × 384 dot product —
microseconds — and the vectors already have somewhere to live, as a JSON array
on the CV row. A vector DB would add an index to keep in sync, a service to
deploy, and a second source of truth for data that is already tiny and
per-tenant. The right time to add one is when a single query has to search
across users, which this product never does.

**Embeddings run locally; only the analysis costs money.** `bge-small-en-v1.5`
on CPU picks the CV. That step is free and instant, so the expensive Gemini call
only ever sees the one CV that matters, instead of all ten.

**No agents, no LangGraph.** The pipeline is a fixed two-call sequence with no
branching, no tool selection, and no loop. An agent would add latency and
non-determinism to buy a flexibility the problem does not have. LCEL expresses
the whole thing in about fifteen lines.

**The logic layer is MCP-ready.** `chains.py`, `embeddings.py` and `store.py`
import nothing from FastAPI, and `run_analysis(vacancy_text, candidates)` takes
plain dataclasses rather than ORM rows or request objects. Wrapping the same
functions in a `FastMCP` server means writing tool decorators, not refactoring.

**Pydantic schemas drive all three layers.** The same `VacancyAnalysis` model is
the LLM's structured-output contract, the FastAPI response model, and the shape
mirrored in `frontend/lib/types.ts`. A field cannot drift between the model and
the UI without the API failing validation first.

**One mock switch, and tests never call the LLM.** `USE_MOCK_LLM` short-circuits
both Gemini and the HuggingFace download to a fixture analysis and a
deterministic hashing embedder. That is what the test suite runs against, and it
is why the whole frontend was built before the first API call was made. Where
the chain graph itself needs testing, the tests patch `structured_llm` — the one
seam every model call goes through — and assert on the prompts it receives.

**Sub-scores are derived, not asked for.** The three bars on the hero card
(profile / skills / summary) come from `derive_sub_scores`: keyword coverage and
a severity-weighted gap penalty. Asking the model for them would let them
contradict `fit_score`, which is the number that actually matters, and would
cost tokens for presentation detail.

**Cross-user isolation is a structural property, not a habit.** There is no
`get_cv(cv_id)` in `store.py` — every accessor takes `user_id` and filters on
it, so a route physically cannot read another account's data by forgetting a
`where` clause. Tests assert that one user gets 404, not 403, for another user's
CVs and analyses.

**argon2 with a signed cookie, not JWT-in-localStorage.** Passwords are hashed
with `argon2-cffi`; the session is a `itsdangerous`-signed, HTTP-only cookie
carrying only a user id. No token is reachable from JavaScript, and there is no
session table to expire.

**CPU-only torch in the image.** The default PyPI `torch` wheel pulls the entire
CUDA stack — about 2.5GB a Railway container can never use. The Dockerfile
installs from the PyTorch CPU index first, then everything else.

**Limits assume the Gemini key is shared.** The deployed demo runs on one API
key, so per-user daily analysis limits, a CV quota, a vacancy length cap and an
upload size cap are all enforced server-side and returned as typed errors the UI
can render specifically.

---

## Deployment

Split deploy: static frontend on Vercel, container backend on Railway.

### Backend → Railway

1. New project → Deploy from repo, **root directory `backend/`**. Railway
   detects the `Dockerfile`.
2. Add a **PostgreSQL** plugin to the project.
3. Set the service variables:

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}`, rewritten to start `postgresql+psycopg://` |
   | `GOOGLE_API_KEY` | your Gemini key |
   | `SECRET_KEY` | a fresh 48-byte random string |
   | `ALLOWED_ORIGINS` | `https://<your-app>.vercel.app,http://localhost:3000` |
   | `PUBLIC_APP_URL` | `https://<your-app>.vercel.app` |
   | `ENVIRONMENT` | `production` |
   | `USE_MOCK_LLM` | `false` |

   Railway's `DATABASE_URL` starts with `postgresql://`, which SQLAlchemy maps to
   psycopg2. Change the scheme to `postgresql+psycopg://` to use the psycopg 3
   driver this project depends on.
4. `PORT` is injected automatically; the container binds to it.

The embedding model is baked into the image, so no volume mount is needed — the
only persistent state is Postgres.

