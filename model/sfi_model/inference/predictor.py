"""Advisory price inference, separate from margins and bid submission."""

import math
import threading
from pathlib import Path

import torch

from sfi_model.features.schema import build_features
from sfi_model.inference.model_bundle import load_model_bundle


class FreightPredictor:
    def __init__(self, bundle: Path):
        self.loaded = load_model_bundle(bundle)
        self._lock = threading.Lock()

    def predict(self, shipment: dict) -> dict:
        features = build_features(shipment)
        encoded = self.loaded.preprocessing.transform([features])
        with self._lock, torch.inference_mode():
            rpm = self.loaded.model(torch.from_numpy(encoded)).item()
        total = rpm * float(features["distance_miles"])
        if not math.isfinite(rpm) or rpm <= 0 or not math.isfinite(total) or total <= 0:
            raise RuntimeError("Prediction must be finite and positive in RPM and total dollars")
        return {
            "api_version": "v1",
            "model_version": self.loaded.metadata["model_version"],
            "predicted_bid_rpm": rpm,
            "predicted_bid_dollars": total,
            "currency": "USD",
            "distance_basis": "loaded_miles",
            "advisory_only": True,
            "release_status": self.loaded.metadata["release_status"],
        }
