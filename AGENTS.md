# Repository Guidelines

## Project Structure & Module Organization
- `app/main.py` defines the FastAPI app and HTTP routes.
- `app/core/` holds cross-cutting utilities: `config.py` (env settings via dotenv), `db.py` (SQLAlchemy engine), and `auth.py` (JWT header check).
- `app/repositories/` contains SQL access with typed row dataclasses.
- `app/services/` encapsulates business logic and external integrations.
- `app/schemas/` provides Pydantic request/response models.
- `app/models/` hosts domain row models used by repositories.
- No `tests/` directory exists yet.

## Build, Test, and Development Commands
- `python -m venv env && source env/bin/activate` creates/activates the local virtualenv used by `runme.sh`.
- `pip install -r requirements.txt` installs runtime dependencies.
- `./runme.sh` runs the API with `uvicorn` and reload by default; customize with `HOST`, `PORT`, and `RELOAD=0`.
- `uvicorn app.main:app --reload` is the direct dev server command if you prefer not to use `runme.sh`.

## Coding Style & Naming Conventions
- Python, 4-space indentation, and PEP 8 conventions; use type hints (`str | None`) as in existing code.
- Keep HTTP inputs/outputs in `app/schemas/`, data access in `app/repositories/`, and non-trivial logic in `app/services/`.
- Use snake_case for variables/functions and PascalCase for classes; match existing dataclass and Pydantic patterns.
- APIs should follow SOLID principles (clear separation of responsibilities, dependency injection, small cohesive modules).
- Database access must use native SQL (no ORM usage).
- Any new or updated endpoint must be documented in `API.md` with example request and response payloads.

## Testing Guidelines
- No testing framework is configured yet. If adding tests, introduce a `tests/` folder and name files `test_*.py`.
- Prefer small, isolated tests for repository SQL and service logic; document any new test command in this file.

## Commit & Pull Request Guidelines
- Git history shows placeholder commit messages (e.g., "."), so no formal convention exists; use short, imperative summaries going forward.
- PRs should describe user-facing behavior changes, list new endpoints or schema changes, and include config/env updates when applicable.

## Security & Configuration Tips
- Local config is read from environment variables (dotenv is enabled). Common settings: `POSTGRES_DSN`, `GRAPH_API_KEY`, `GRAPH_SUBGRAPH_ID_*`, and `PRICE_OVERRIDES`.
- All API routes expect a `Bearer` token in `Authorization`; keep this in mind when testing endpoints locally.
- Use `.env.example` as the template; never commit secrets.

## Response Language
- Always respond in Portuguese.
