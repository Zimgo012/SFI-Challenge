"""Versioned advisory pricing router for the existing FastAPI application."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class BidPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    order_type: Literal["open_bid"] = "open_bid"
    distance_miles: float = Field(gt=0)
    weight_lbs: float = Field(gt=0)
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)
    lane_id: str = Field(min_length=1)
    origin_state: str = Field(min_length=1)
    destination_state: str = Field(min_length=1)


class BidPredictionResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    api_version: Literal["v1"]
    model_version: str
    predicted_bid_rpm: float = Field(gt=0)
    predicted_bid_dollars: float = Field(gt=0)
    currency: Literal["USD"]
    distance_basis: Literal["loaded_miles"]
    advisory_only: Literal[True]
    release_status: Literal["unverified"]


def create_pricing_router(bundle_path: Path | None = None) -> APIRouter:
    """Load once per lifespan; model failures leave ordinary backend routes available."""
    predictor = None

    @asynccontextmanager
    async def lifespan(app):
        nonlocal predictor
        try:
            configured = os.getenv("SFI_MODEL_BUNDLE") or bundle_path
            if configured:
                # Keep optional PyTorch imports out of the backend's ordinary import path.
                from sfi_model.inference.predictor import FreightPredictor

                predictor = await asyncio.to_thread(FreightPredictor, Path(configured))
            else:
                logger.info("SFI_MODEL_BUNDLE unset; advisory pricing unavailable")
        except Exception:
            logger.exception("Advisory model initialization failed")
            predictor = None
        try:
            yield
        finally:
            predictor = None

    router = APIRouter(prefix="/api/v1", tags=["Advisory pricing"], lifespan=lifespan)

    @router.post("/predict-bid", response_model=BidPredictionResponse)
    def predict_bid(shipment: BidPredictionRequest):
        if predictor is None:
            raise HTTPException(503, detail={"code": "MODEL_UNAVAILABLE", "action": "REVIEW"})
        try:
            return predictor.predict(shipment.model_dump(exclude={"order_type"}))
        except ValueError as error:
            raise HTTPException(422, detail={"code": "INVALID_MODEL_INPUT"}) from error
        except Exception as error:
            logger.exception("Advisory pricing inference failed")
            raise HTTPException(503, detail={"code": "MODEL_ERROR", "action": "REVIEW"}) from error

    return router
