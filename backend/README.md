# VacancyScore Backend

FastAPI handles Supabase authentication, CV storage and parsing, Gemini
analysis and embeddings, and PDF reports.

The backend is deployed with the Next.js frontend as **one Vercel project**
from the repository root. The Vercel entrypoint is ../api/index.py and the
public route prefix is /api. This directory is not a separate Vercel project.

Use the [root README](../README.md) for local commands, environment variables,
database initialization, checks and deployment instructions.
