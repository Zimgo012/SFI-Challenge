"""Versioned model-service contracts; the installed local package owns their format."""
from sfi_model.api.autopilot import AutopilotRequest as PairRequest
from sfi_model.api.live import LiveBatchRequest as ModelBatchRequest
from sfi_model.api.live import LiveBatchResponse as ModelBatchResponse

__all__ = ['PairRequest', 'ModelBatchRequest', 'ModelBatchResponse']
