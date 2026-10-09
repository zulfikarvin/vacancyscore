# VacancyScore

VacancyScore compares vacancies with stored CVs, explains the match and gaps,
and exports analysis as PDF.

## One Vercel project

The repository root is one Next.js project. Vercel builds the UI and the Python
API together and serves both on the same domain:

```text
Browser -> https://your-app.vercel.app
           /          Next.js UI
           /api/*     FastAPI Python function
                         |-- Supabase Auth and PostgreSQL
                         `-- Gemini analysis and embeddings
```

There is no separate backend Vercel project and no BACKEND_API_URL setting.

## Structure

```text
src/
  app/                   Next.js pages and styles
  components/            UI components
  lib/                   Typed API client and shared frontend types
api/index.py             Vercel Python entrypoint, mounts FastAPI at /api
backend/
  app/                   Backend routes, auth, storage and analysis
  tests/                 Backend and deployment-entrypoint tests
  pyproject.toml         Python project and dependency source
  .env.example           Backend configuration template
  check_database.py      Database initialization and upgrades
package.json             Frontend dependencies and root commands
package-lock.json        Locked frontend dependencies
requirements.txt         Generated, pinned Python runtime dependencies
.python-version          Python version for Vercel
next.config.ts           Local /api proxy to port 8000
vercel.json              Next.js preset and same-project /api routing
```

## Local development

Requirements: Node.js 20+, Python 3.12, and uv.

Run from the repository root:

```powershell
npm install
# Only on first setup; do not overwrite an existing configured backend/.env:
Copy-Item backend/.env.example backend/.env
uv venv backend/.venv --python 3.12
uv pip install --python backend/.venv/Scripts/python.exe -r requirements.txt pytest
npm run dev:api
```

Fill in backend/.env before starting the API. In a second terminal at the root:

```powershell
npm run dev
```

Open http://localhost:3000. The browser calls /api on port 3000 and Next.js
proxies to FastAPI on port 8000. The local health URL is
http://localhost:3000/api/health. Backend configuration is loaded from
backend/.env regardless of the working directory.

Your existing backend/.env can continue to be used. Frontend environment files
are unnecessary for this setup. The old frontend directory may still contain
ignored local build caches and node_modules; it is no longer application source
and is excluded from Vercel uploads and the Python function bundle.

## Deploy to Vercel

1. Push this repository including the root package.json, package-lock.json,
   requirements.txt, api/, src/, backend/app/, and vercel.json.
2. Import the repository as **one Vercel project**. If reusing your existing
   frontend project, change its **Root Directory** from frontend to the
   repository root (leave the field empty). Select **Next.js** as the framework.
3. Clear old build/install/output overrides. The defaults are npm install,
   npm run build, and Next.js's output directory. Use Node.js 22.x or newer.
4. Add the environment variables below to that one project. Remove any obsolete
   BACKEND_API_URL or NEXT_PUBLIC_API_URL variables.
5. Initialize the database once from your local machine using your working
   backend/.env:

   ```powershell
   uv run --directory backend --no-sync python check_database.py
   ```

6. Deploy. Open https://YOUR-APP.vercel.app/api/health and confirm status is ok.
   The API documentation is at /api/docs.
7. In Supabase Authentication URL Configuration, set Site URL to your app URL
   and add https://YOUR-APP.vercel.app/reset-password to Redirect URLs. Keep
   http://localhost:3000/reset-password for local development.
8. Test signup/login, CV upload, analysis, PDF download, logout and recovery.

Set these values in Vercel Settings -> Environment Variables:

| Variable | Value |
| --- | --- |
| DATABASE_URL | Supabase transaction-pooler URI, with URL-encoded password and sslmode=require |
| NEXT_PUBLIC_SUPABASE_URL | Supabase project URL |
| NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY | Supabase publishable/anon key |
| GOOGLE_API_KEY | Gemini API key |
| GEMINI_MODEL | Your available structured-analysis model; see backend/.env.example |
| GEMINI_EXTRACTION_MODEL | Your available extraction model; see backend/.env.example |
| EMBEDDING_MODEL | gemini-embedding-001 |
| ENVIRONMENT | production |
| USE_MOCK_LLM | false |
| PUBLIC_APP_URL | https://YOUR-APP.vercel.app |
| ALLOWED_ORIGINS | https://YOUR-APP.vercel.app,http://localhost:3000 |

Vercel provides VERCEL automatically; do not set it locally. Schema changes are
run through check_database.py, not at serverless cold start. Never use SQLite
for deployed persistence. Although the Supabase variables retain their old
NEXT_PUBLIC names, the frontend does not read them; auth is handled by Python.

The Python function has a 300-second maximum duration. Uploads remain limited
to 4 MB in the backend to fit Vercel request limits. Credentials stay in
Vercel environment settings, never in version control.

## Checks and dependency updates

```powershell
npm run build
npm run lint
npm run test:backend
```

After changing backend runtime dependencies, regenerate the root lock file:

```powershell
uv pip compile backend/pyproject.toml --python-version 3.12 --universal --output-file requirements.txt
```

Vercel installs Python dependencies from requirements.txt. Keep this generated
file committed together with backend/pyproject.toml. The Python runtime excludes
frontend packages, build output, tests, local databases and environment files.

## Stored CV migration

Older CV vectors are regenerated automatically when needed. To upgrade all
stored vectors explicitly, run:

```powershell
uv run --directory backend --no-sync python reembed_cvs.py
```

This calls Gemini for each CV when real analysis is enabled.

## Deployment references

- [Vercel: Python and JavaScript in one application](https://vercel.com/kb/guide/how-to-use-python-and-javascript-in-the-same-application)
- [Vercel: Python functions in the api directory](https://vercel.com/docs/functions/runtimes/python/api-directory)
