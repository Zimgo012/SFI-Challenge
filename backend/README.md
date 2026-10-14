# SFI Challenge Backend

FastAPI backend managed with uv. Requires Python 3.13+ and
[uv](https://docs.astral.sh/uv/getting-started/installation/).

## Local development

Run these commands from the backend directory:

```sh
uv sync --locked
uv run uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Open `/docs` for Swagger UI,
`/redoc` for ReDoc, or `/openapi.json` for the OpenAPI document.
`GET /health` returns `{"status": "ok"}` as a basic liveness check.

You can also start the development server with `uv run python main.py`.
To run without automatic reload:

```sh
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## Project structure

```text
main.py                         # Application creation and router registration
schema/health_schema.py          # Pydantic schemas and model definitions
service/health_service.py        # Business logic
controller/health_controller.py  # FastAPI routes
tests/test_health.py             # HTTP and OpenAPI integration tests
pyproject.toml                   # Project metadata and dependencies
uv.lock                          # Resolved dependency versions
```

Keep each feature's schemas/models in `schema/`, logic in `service/`, and
routes in `controller/`. Use matching names such as `user_schema.py`,
`user_service.py`, and `user_controller.py`. Controllers handle HTTP concerns
and call services; services must not import controllers. Register new routers
with `app.include_router(...)` in `main.py`.

## Dependencies and tests

```sh
uv add <package>                # Add a runtime dependency
uv add --dev <package>          # Add a development dependency
uv run python -m unittest discover -s tests -v
```

Commit `pyproject.toml` and `uv.lock` together when dependencies change.
uv creates `.venv/` automatically; keep it and local secrets out of Git.
Tests use standard-library `unittest` and FastAPI's HTTPX-backed TestClient.

The layout uses FastAPI's documented
[APIRouter approach](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
and uv's [project workflow](https://docs.astral.sh/uv/guides/projects/).
