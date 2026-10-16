import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
import os
from urllib.parse import urlsplit

from dotenv import dotenv_values
import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from schema.price_analysis import (
    ModelBackendEconomics, ModelManualRequest, ModelManualResponse, ModelPriceAdvice,
    ModelShipmentFeatures, ModelWarningPolicy, PriceAnalysisError, PriceAnalysisResult,
)
from schema.shipment import Shipment
from service.database import PROJECT_ROOT
from service.dispatch_policy import evaluate_dispatch
from service.errors import ProductError

MODEL_PATH = 'api/v1/manual-mode/evaluate'


def analysis_settings():
    config = dotenv_values(PROJECT_ROOT / '.env')
    def value(key, default):
        return os.environ.get(key, config.get(key, default))
    url = value('MODEL_API_URL', '').strip().rstrip('/')
    parsed = urlsplit(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.port == 0
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('MODEL_API_URL must be an HTTP(S) base URL without credentials, query, or fragment')
    timeout = float(value('MODEL_API_TIMEOUT_SECONDS', '10'))
    deviation = float(value('MODEL_MAX_REFERENCE_DEVIATION_PCT', '25'))
    if not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise ValueError('MODEL_API_TIMEOUT_SECONDS must be greater than 0 and at most 120')
    if not math.isfinite(deviation) or deviation < 0:
        raise ValueError('MODEL_MAX_REFERENCE_DEVIATION_PCT must be finite and nonnegative')
    return url, timeout, deviation


def model_number(value):
    """Never silently change a cent amount to satisfy the model's float API."""
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or Decimal(str(number)) != Decimal(str(value)):
        raise ValueError('A backend amount cannot be represented unchanged by the model API')
    return number


def unavailable(result, code, message, *, http_status=None, fields=None):
    result.error = PriceAnalysisError(code=code, message=message, http_status=http_status, fields=fields or [])
    result.advisory_status = 'unavailable'
    return result


def prepare_analysis(engine, external_id, request):
    """Read one local snapshot; close its transaction before any model HTTP."""
    try:
        with Session(engine, autoflush=False) as session:
            shipment = session.scalar(select(Shipment).where(Shipment.external_id == external_id))
            if shipment is None:
                raise ProductError(404, 'Order not found')
            if shipment.order_type != 'open_bid':
                raise ProductError(422, 'The configured price model supports open-bid orders only')
            evaluation = evaluate_dispatch(session, shipment, request.bid_rate, request.unit_id)
            lane = request.lane_id
            source = 'request' if lane else 'missing'
            codes = [(code or '').strip().upper() for code in (
                shipment.origin_terminal_code, shipment.destination_terminal_code,
            )]
            if lane is None and all(code.lower() not in ('', 'na', 'n/a', 'null', 'none', 'nan') for code in codes):
                lane = '-'.join(codes)
                source = 'board_terminal_codes'
            result = PriceAnalysisResult(
                request_id=request.request_id, external_id=external_id, bid_rate=request.bid_rate,
                requested_unit_id=request.unit_id, order_last_synced_at=shipment.last_synced_at,
                analyzed_at_wall=datetime.now(timezone.utc), lane_id_source=source,
                deterministic_evaluation=evaluation,
            )
            features = {field: getattr(shipment, field) for field in (
                'distance_miles', 'weight_lbs', 'origin_latitude', 'origin_longitude',
                'destination_latitude', 'destination_longitude', 'origin_state', 'destination_state',
            )}
            for field in ('distance_miles', 'weight_lbs', 'origin_latitude', 'origin_longitude',
                          'destination_latitude', 'destination_longitude'):
                if features[field] is not None:
                    features[field] = float(features[field])
            try:
                shipment_features = ModelShipmentFeatures(**features, lane_id=lane)
            except ValidationError as exc:
                fields = sorted({'.'.join(str(part) for part in item['loc']) for item in exc.errors()})
                return unavailable(result, 'MODEL_INPUTS_MISSING_OR_INVALID',
                                   'Correct the missing or invalid shipment features before requesting model advice.', fields=fields)
            try:
                economics = evaluation.economics
                result.model_request = ModelManualRequest(
                    shipment=shipment_features, manual_bid_dollars=model_number(request.bid_rate),
                    backend_economics=ModelBackendEconomics(
                        total_estimated_cost_dollars=model_number(economics.total_cost),
                        gross_profit_dollars=model_number(economics.gross_profit),
                        margin_percent=model_number(economics.margin_pct),
                    ), warning_policy=ModelWarningPolicy(),
                )
            except (ValueError, OverflowError):
                return unavailable(result, 'MODEL_AMOUNT_PRECISION_UNSUPPORTED',
                                   'The model API cannot represent these economics unchanged; use the deterministic result.')
            return result
    except SQLAlchemyError as exc:
        raise ProductError(503, 'Product database is unavailable or not migrated; start the dispatcher and apply migrations') from exc


def make_model_client(url, timeout):
    return httpx.AsyncClient(base_url=url + '/', timeout=timeout, follow_redirects=False)


async def analyze_price(engine, external_id, request):
    result = await asyncio.to_thread(prepare_analysis, engine, external_id, request)
    if result.error is not None:
        return result
    try:
        url, timeout, deviation = analysis_settings()
    except (ValueError, TypeError, AttributeError):
        return unavailable(result, 'MODEL_CONFIGURATION_INVALID', 'Configure MODEL_API_URL and valid model timeout/deviation settings in .env.')
    policy = result.deterministic_evaluation.policy
    try:
        result.model_request.warning_policy = ModelWarningPolicy(
            minimum_profit_dollars=model_number(policy.min_expected_margin_usd) if policy.enforce_margin else None,
            minimum_margin_percent=model_number(policy.min_expected_margin_pct) if policy.enforce_margin and policy.min_expected_margin_pct < 100 else None,
            maximum_reference_deviation_percent=deviation,
        )
    except (ValueError, OverflowError):
        return unavailable(result, 'MODEL_AMOUNT_PRECISION_UNSUPPORTED', 'The model API cannot represent the configured thresholds unchanged.')
    if policy.enforce_margin and policy.min_expected_margin_pct == 100:
        result.warnings.append('The model warning API cannot express a 100% minimum margin; the backend still enforces that threshold.')
    payload = result.model_request.model_dump(mode='json')
    try:
        async with asyncio.timeout(timeout), make_model_client(url, timeout) as client:
            response = await client.post(MODEL_PATH, json=payload, headers={'X-Request-Id': str(request.request_id)})
    except (TimeoutError, httpx.TimeoutException):
        return unavailable(result, 'MODEL_TIMEOUT', 'Price analysis timed out; deterministic economics remain available.')
    except httpx.RequestError:
        return unavailable(result, 'MODEL_CONNECTION_FAILED', 'The model API is unreachable; deterministic economics remain available.')
    result.prediction_id = response.headers.get('X-Prediction-Id')
    if response.status_code != 200:
        return unavailable(result, 'MODEL_HTTP_ERROR', 'The model API could not analyze this request; deterministic economics remain available.', http_status=response.status_code)
    try:
        if len(response.content) > 1_048_576:
            raise ValueError('Oversized model response')
        data = response.json()
        # Reject nonfinite numbers even inside extensible model metadata.
        json.dumps(data, allow_nan=False)
        model_response = ModelManualResponse.model_validate(data)
        echo = model_response.backend_economics.model_dump(mode='json')
        if (model_response.manual_bid_dollars != payload['manual_bid_dollars']
                or echo != payload['backend_economics']):
            raise ValueError('The model changed the manual bid or backend economics')
        result.model_response = model_response
        if isinstance(model_response.advisory, ModelPriceAdvice):
            result.advisory_status = model_response.advisory.pricing_source
        else:
            unavailable(result, 'MODEL_ADVISORY_UNAVAILABLE', 'The model returned unavailable advice; review its error details.',
                        http_status=model_response.advisory.http_status)
    except (ValueError, TypeError, ValidationError):
        return unavailable(result, 'MODEL_INVALID_RESPONSE', 'The model returned an invalid response or changed the supplied economics.')
    return result
