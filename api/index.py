"""Same-project Vercel entrypoint for all /api/* requests.

Vercel retains the original request path when rewriting to this function.
The mount strips /api before handing the request to the existing backend.
"""

import sys
from pathlib import Path

from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app as backend_app  # noqa: E402

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=backend_app.router.lifespan_context,
)
app.mount("/api", backend_app)
