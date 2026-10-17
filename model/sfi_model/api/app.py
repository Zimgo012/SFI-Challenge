"""Optional project-local ASGI entry point; embedding the router remains supported."""

from fastapi import FastAPI

from sfi_model.api.pricing import create_pricing_router
from sfi_model.paths import PROJECT_ROOT

app = FastAPI(title="SFI Advisory Pricing API", version="v1")
app.include_router(
    create_pricing_router(
        PROJECT_ROOT / "artifacts/models/freight-rpm-v1",
        range_path=PROJECT_ROOT / "artifacts/baselines/historical-range-v1.json",
    )
)
