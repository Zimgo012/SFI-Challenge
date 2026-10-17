# SFI PyTorch workspace

Source code is grouped by domain under `sfi_model/`, with matching test folders:

```text
sfi_model/
  data/          # validation, open-bid preparation, chronological splitting
  features/      # feature schema and shared preprocessing
  models/        # small positive-output freight RPM regressor
  baselines/     # training-only non-ML pricing references
  evaluation/    # baseline metrics; freight evaluation scaffold
  inference/     # versioned bundles and advisory predictor
  api/           # pricing router embedded in the existing backend
  training/      # seeded setup, freight fitting/tuning, synthetic example
  paths.py       # shared project paths
tests/
  data/
  features/
  models/
  baselines/
  evaluation/
  inference/
requirements/
  data/
  model/
  operations/
  evaluation/
  baselines/
  inference/
  requirements.md  # master checklist
```

Run domain commands with `python -m` from this directory. `main.py` delegates to
the training example. The root `data/` and `artifacts/` folders hold local inputs
and generated outputs, separate from the source packages.

Python 3.11–3.13 workspace with PyTorch, NumPy, pandas, scikit-learn, and Matplotlib.
The included example trains a small binary classifier on synthetic data, evaluates
on a held-out validation set, and saves a checkpoint. No dataset download is needed.

Freight section 4 is complete, including training, evaluation, packaging, and
loading/prediction parity tests. Section 5.1 now mounts advisory prediction in the
existing backend; section 5 validation, fallback and logging are complete.
Section 6 Manual Mode exposes a project-local API contract. Section 7 now has an
authenticated live-only Autopilot decision API; backend dispatch wiring and final
submission safeguards remain backend responsibilities.
See `requirements/model/pipeline-layout.md` for the module map and current status.

## Setup

From this directory, using [uv](https://docs.astral.sh/uv/):

```sh
uv sync
uv run python main.py
```

`uv sync` creates `.venv` and installs the versions recorded in `uv.lock`, including
the Ruff development tool. In PyCharm, select `.venv/bin/python` as the project
interpreter. Do not commit the virtual environment, datasets, or generated outputs.

For pip instead:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python main.py
```

The pip workflow resolves the dependency ranges in `pyproject.toml`; use uv for the
locked environment. Installation follows the [PyTorch macOS guidance](https://pytorch.org/get-started/locally/).
For a CUDA workstation, choose the wheel index appropriate for its driver from that guide.

## Historical data validation

```sh
uv run python -m sfi_model.data.validation --expected-rows 2500
uv run python -m unittest discover -s tests
```

The validator reads `data/historical_shipments.csv` without changing it and writes
`artifacts/data-validation.json`. It checks the schema, row shape, required and
optional missing values, numeric ranges, categories, duplicate IDs/records, and
shipment dates. Exit code 1 indicates validation errors; warnings preserve data
for review. Use `--data`, `--output`, and `--as-of YYYY-MM-DD` to override paths and
the future-date cutoff. Expected row count is optional and should change when the
dataset changes. Currency and source unit semantics still need producer confirmation.

See `requirements/data/data-validation.md` for the initial validation findings.

## Open-bid population selection

```sh
uv run python -m sfi_model.data.preparation
```

This selects validated `open_bid` records, including both awarded and lost bids,
and excludes `fixed_rate` and invalid records. Outputs are
`artifacts/prepared/open_bid_shipments.csv` and `selection-report.json` in the same
directory. The audit records counts, exclusion reasons, and optional missingness.
Empty or absent optional fields do not remove otherwise valid rows; fully empty
export helpers stay out of model inputs and are not imputed as zero.
Use `--data`, `--output-dir`, or `--as-of YYYY-MM-DD` to override
defaults. The staging CSV appends `target_bid_rpm = bid_rate / distance_miles`
without rounding, and the report includes its units and range. It retains source
columns for audit. Model-facing exports are separate: `model_features.csv`
contains only the explicit nine-column shipment/lane allowlist; `model_targets.csv`
contains only `target_bid_rpm`; `model_metadata.csv` contains shipment ID and date
for audit and future splitting. Keep these files aligned by row position and
never feed staging or metadata columns into the model. Unknown/new CSV columns
are excluded by default. See `requirements/model/model-input-boundaries.md` for exclusions.
`main.py` still runs the synthetic setup example.

## Chronological splits and preprocessing

```sh
uv run python -m sfi_model.data.splitting
```

This creates `artifacts/dataset/` with chronological train/validation/test partitions
(70/15/15 by default), keeping identical shipment timestamps together. The initial
split contains 756/162/163 rows. Numerical scaling and one-hot category encoding
are fitted on training features only; validation/test use the saved transform.
Each partition has aligned raw CSVs and float32 `X`/`y` in `arrays.npz`.
The training-fitted processor is `preprocessor.pkl`; `split-report.json` records
IDs, date ranges, feature names, and source/version information. Existing output
directories are preserved; use a new `--output-dir` for an intentional new version.
Keep test reserved for one final evaluation, and tune using validation only.
See `requirements/data/chronological-partitions.md` for options and artifact details.

## Saved inference preprocessing

```sh
uv run python -m sfi_model.inference.bundle
```

Exports an existing dataset's training-fitted preprocessor into
`artifacts/inference/v2/`, alongside its schema, units, category mappings, scaler
statistics, missing-value policy, and version/checksum manifest. Existing bundles
are preserved; use a new `--output-dir` for a later version. New split runs also
save a bundle in their dataset's `inference/` folder.

Use `load_inference_bundle(Path("artifacts/inference/v2"))` from `sfi_model.inference.bundle`
and call `.transform([shipment])` to obtain the encoded float32 inputs without
refitting. Load using the locked training environment; incompatible versions or
changed artifacts are rejected. See `requirements/inference/inference-artifacts.md` for a
complete example. This bundle contains preprocessing, not trained pricing weights.

## Global median pricing baseline

```sh
uv run python -m sfi_model.baselines.global_median
```

Fits the median of `train/targets.csv` only, checking its alignment and provenance
against the training metadata and split manifest. The current reference is
**2.9090003985451105 USD/mile** from 756 training records, saved in
`artifacts/baselines/global-median-v1.json`. No validation/test files are read.
Use a new `--output` path for another version; existing artifacts are preserved.
See `requirements/baselines/global-median.md` for the reusable loader.

## Lane median pricing baseline

```sh
uv run python -m sfi_model.baselines.lane_median --min-lane-samples 5
```

Uses training data only. Lanes with at least five examples use their own median;
sparse and unseen lanes use the global training median. The current artifact,
`artifacts/baselines/lane-median-v1.json`, contains 41 eligible and 47 sparse lanes.
The sample threshold is configurable; choose a new `--output` when changing it.
`load_lane_median(...).predict(lane_id)` returns RPM, reference source, sample count,
and fallback reason. See `requirements/baselines/lane-median.md` for details.

## Conditional market-RPM baseline

```sh
uv run python -m sfi_model.baselines.market_rpm
```

Saves `artifacts/baselines/market-rpm-v1.json`. The baseline uses an approved,
finite-positive USD/loaded-mile quote only when its observation/publication times
precede the bid and its freshness and shipment/lane checks pass. It never fits
against bids or silently substitutes another price.

The current CSV's RPM helpers are offer-derived, so this baseline is explicitly
unavailable until an independent pre-bid feed/snapshot is supplied. See
`requirements/baselines/market-rpm.md` for the quote contract and loader.

## Validation bid-dollar comparisons

```sh
uv run python -m sfi_model.evaluation.bid_comparison
```

Converts saved global/lane RPM references to dollars using loaded miles and
compares them with original submitted bids for the 162 validation shipments.
Outputs `comparisons.csv` and `report.json` in
`artifacts/evaluation/validation-bids-v1/`; choose a new `--output-dir` to rerun.
Unrounded and cent-rounded predictions are recorded separately. Market quotes
remain unavailable, and test files are not read. Aggregate/slice MAE is a later task.
See `requirements/evaluation/bid-comparisons.md` for comparison semantics.

## Validation MAE and slices

```sh
uv run python -m sfi_model.evaluation.validation_metrics
```

Saves `metrics.json`, `overall.csv`, and `slices.csv` in
`artifacts/evaluation/validation-metrics-v1/`. Reports RPM and total-dollar MAE,
coverage, bias, and sample counts overall and by lane, training-derived distance
and weight bands, and retrospective shipment season. Sparse slices are flagged;
unavailable predictions and unobserved seasons have no fabricated score.
The reserved test partition is not evaluated. See
`requirements/evaluation/validation-mae.md` for the current results and limitations.

## Selected baseline fallback

```sh
uv run python -m sfi_model.baselines.fallback
```

Records the validation metrics and selects lane median with global fallback in
`artifacts/baselines/fallback-policy-v1.json`. The selected policy has complete
validation coverage and lower RPM/dollar MAE than global alone. The baseline
artifact is pinned by hash; missing or changed artifacts route to review.

`recommend_fallback` from `sfi_model.baselines.fallback` provides advisory RPM and
total-dollar candidates for explicit model-failure/unreliable triggers when the
effective policy enables baseline fallback. Inputs must be supported; all
profitability/fleet checks and submission authorization remain separate. See
`requirements/baselines/selected-fallback.md` for the invocation and recorded evidence.

## Freight Dataset and DataLoader

`create_train_validation_loaders` from `sfi_model.data.dataset` loads saved
training/validation arrays as float32 PyTorch batches. It validates CSV/array
alignment and the fitted preprocessing contract, shuffles training reproducibly,
preserves validation order, and retains final partial batches. It does not open
test data or train a model. See `requirements/model/dataset-loaders.md` for usage.

## Freight MLP architecture

`FreightRPMRegressor` and `RegressorConfig` in `sfi_model.models.regressor` define
the small `114 -> 32 -> 16 -> 1` default network (4,225 parameters). Softplus plus
a small numerical floor produces one positive RPM per shipment, matching the
Dataset's scalar targets. The first training run is saved in `artifacts/training/freight-tuning-v1/`. See
`requirements/model/regressor.md` for construction and input/output details.

## Freight loss, optimizer, and seeds

`build_training_components` in `sfi_model.training.setup` initializes the model
with seed 42, Huber loss (delta 0.5), and AdamW (learning rate 0.003, weight decay
0.01). Settings are validated and configurable; deterministic algorithms are
enabled by default. It creates components without training or reading held-out data.
Use the same seed for the DataLoaders. See `requirements/model/training-setup.md`.

## Freight training and validation-only tuning

```sh
uv run python -m sfi_model.training.regression
```

Training now monitors validation Huber loss each epoch, stops after 25 epochs
without improvement greater than 0.0001, and restores the lowest-loss checkpoint.
The maximum is 300 epochs per candidate; learning rates are 0.003 and 0.001.
The completed run is in `artifacts/training/freight-earlystop-v1/`: selected epoch
47, validation MAE **0.272870 RPM** and **$301.28** on 162 records, after training
on 756 records. Final test evaluation is now complete; see below.

Each candidate saves `best.pt` and `history.csv`. The run saves `selected-best.pt`,
configuration/provenance, validation predictions, and `loss-curves.png` / `.svg`.
Use a new `--output-dir` to run again; existing directories are preserved:

```sh
uv run python -m sfi_model.training.regression --output-dir artifacts/training/freight-earlystop-v2
```

Options include `--epochs`, `--patience`, and `--min-delta`. The earlier fixed
150-epoch run remains in `artifacts/training/freight-tuning-v1/`.
See `requirements/model/early-stopping.md` for checkpoint and logging semantics.

## Final chronological test evaluation

The selected epoch-47 model was evaluated once on all 163 test shipments:
**0.274773 RPM MAE**, **$297.35 dollar MAE**, and **100% coverage**.
`artifacts/training/freight-earlystop-v1/` contains `final-test-plan.json`,
`test-results.json`, and `test-predictions.csv`. The plan froze metrics gates before
loading test records. The overall ceilings pass. Baseline/slice comparisons are now complete; the
model remains a research result with no live promotion.

The command `uv run python -m sfi_model.evaluation.final_test` rejects repeat
scoring of this run. Reuse the saved predictions for comparisons; future tuning
requires a fresh holdout. See `requirements/evaluation/final-test.md`.

## PyTorch and baseline comparison

Saved validation/test predictions are compared with the frozen training-only
baselines in `artifacts/evaluation/model-comparison-v1/`. Test MAE is 0.274773 RPM /
$297.35 for PyTorch versus 0.307042 / $368.26 for lane + global: reductions of
**10.51% RPM** and **19.26% dollars**. Short-haul errors are higher; all individual
test lanes are sparse. Overall gates pass, but release status remains **unverified**.
The baseline/review policy is retained.

The directory contains `comparison.json`, `overall.csv`, `slices.csv`,
`predictions.csv`, and `baseline-comparison.png` / `.svg`. Comparisons reuse
training-derived bands and saved predictions without another model pass:

```sh
uv run python -m sfi_model.evaluation.model_comparison --output-dir artifacts/evaluation/model-comparison-v2
```

See `requirements/evaluation/model-comparison.md` for improvements, regressions,
coverage limitations, and gates. Versioned model packaging is now complete (4.9).

## Versioned freight model package

`artifacts/models/freight-rpm-v1/` groups the exact selected checkpoint and training
preprocessor with feature schema/order/units, categorical mappings, missing-value
policy, training metadata, evaluation results, frozen baselines, and the lockfile.
Its manifest pins all 23 payload files and dependency/model-code compatibility.
Release remains **unverified**, with live submissions disabled.

```python
from pathlib import Path
from sfi_model.inference.model_bundle import load_model_bundle

loaded = load_model_bundle(Path("artifacts/models/freight-rpm-v1"))
```

Loading uses only the package and matching installed code/environment. The model
is loaded on CPU in evaluation mode with gradients disabled. A relocated copy
reproduced all 162 saved validation predictions exactly, using batch size 64.

`uv run python -m sfi_model.inference.model_bundle` exports packages; the existing
version is preserved. Use a new `--model-version` for a deliberate separate export.
See `requirements/model/model-packaging.md`. Automated loading and prediction
parity tests (4.10) are complete:

```sh
uv run python -m unittest tests.inference.test_model_predictions
```

Seven synthetic integration tests cover exact saved-model prediction parity,
relocation and fresh-process loading, no fitting/input mutation, and rejection
of altered or incompatible artifacts. All 127 tests pass. See
`requirements/model/prediction-parity.md` for the CPU/environment/batch scope.
Section 4 is complete; next is the versioned prediction API (5.1).

## Run the packaged model and export plots

The validation preview ran successfully on 162 shipments: MAE 0.272870 RPM and
$301.28, reproducing the saved predictions exactly. Outputs are in
`artifacts/evaluation/model-preview-v1/`; `model-preview-v1.zip` exports the folder.

```sh
uv run python -m sfi_model.evaluation.preview --output-dir artifacts/evaluation/model-preview-v2
```

The command runs frozen packaged inference on validation inputs and exports RPM
and dollar prediction scatter plots, an RPM error histogram, dollar errors by
loaded distance, training curves, baseline comparisons, predictions CSV, and a
metrics JSON. Diagnostics include PNG, SVG, and PDF; other charts include PNG/SVG.
The ZIP contains all outputs. Existing preview directories are preserved.
Training curves and baseline/test comparisons reuse package reports. This preview
does not retrain, rescore test records, start the API, or submit bids.

## Advisory prediction in the existing backend

The existing FastAPI app now serves **POST `/api/v1/predict-bid`** through the local
`sfi-model[api]` package. Start it from the backend directory:

```sh
cd ../../backend
uv sync
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

The model loads once per worker at startup. The default is `freight-rpm-v1` in this
project's `artifacts/models/`; `SFI_MODEL_BUNDLE` overrides the bundle path.
Its response supplies advisory `predicted_bid_rpm`, `predicted_bid_dollars`,
model/API version, USD/loaded-mile units, and the unverified release state.
Existing bids, calculator values, and submissions remain backend responsibilities.

From the model directory, with the backend running:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/predict-bid \
  -H 'Content-Type: application/json' \
  --data-binary @artifacts/api/predict-bid-v1/request.json
```

The saved smoke-test response predicts 2.883418 RPM / $2433.32 for a CHI-JAX
validation shipment. Invalid inputs return 422; an unavailable/failed model returns
503 with REVIEW and no price. No server was left running by the smoke test.
All 133 model/API tests and 24 backend regression tests pass. See
`requirements/inference/prediction-api.md` for request fields, lifecycle, and
remaining section 5 work. The combined backend/model environment requires Python
3.13; the model artifacts require their exact recorded runtime versions.

## Pricing request validation

Section 5.2 adds field-specific error codes to pricing requests. All nine features
must be present with finite numeric values, valid coordinates, and positive loaded
miles/weight. Categories are trimmed/uppercased and checked against the saved
training mappings. Missing tokens and unseen lanes/states return HTTP 422 with
REVIEW and no price; the model is not run for unseen categories.

Optional `units` declarations accept only `distance: miles`, `weight: lb`,
`coordinates: degrees`, and `currency: USD`. Omitted declarations follow the named
endpoint units; no conversion or feature imputation occurs. Numeric strings,
booleans, fixed-rate orders, and extra fields are rejected.

Errors contain `detail.code`, `detail.action`, and, for input errors,
`detail.errors` with field/code/message entries. Input values are not echoed.
Internal preprocessing/model failures and invalid outputs return 503 MODEL_ERROR;
other backend routes retain their existing error format. OpenAPI describes the
custom pricing errors.

All 144 model/API tests and 24 backend regression tests pass. Real-package examples
are saved in `artifacts/api/validation-v1/examples.json`. See
`requirements/inference/input-validation.md`. Section 5.3 baseline/support
diagnostics are now complete. Release remains unverified.

## Baseline prices and model-support warnings

Successful pricing responses now include `baseline_reference` with frozen
lane/global RPM and total USD, its source/reason, policy version, training count,
and lane minimum. The smoke-test model suggestion is $2433.32 beside a $2454.91
reference; the lane is sparse, so the response identifies the global median.

`warnings` flag unverified release/lane evidence, sparse baseline lanes, values
more than three training standard deviations from their means (an uncalibrated
heuristic), and saved distance/weight slices with historical baseline regressions.
These are descriptive diagnostics, not new bid/routing decisions.
`support_policy_version` identifies the diagnostic contract. `uncertainty.status`
is `not_calibrated`, with null confidence level and intervals.

Examples are in `artifacts/api/references-v1/`. All 150 model/API tests and 24
backend regression tests pass. See `requirements/inference/pricing-references.md`.
Section 5.4 calculator/submission separation checks are now complete. The model
remains advisory and unverified; safe fallback execution is next (5.5).

## Calculator and submission separation

Section 5.4 adds an import-boundary guard and four dedicated integration tests
against the existing backend app and an isolated temporary database. They prove
pricing does not request a database session, invoke margin calculations, reserve
units, or call submission/board functions. Changing a suggestion from $300 to
$3,000 preserves the manually entered $1,800.12 bid and its full economics.
Model failures leave manual calculation available; submission fields are rejected.

All 151 model/API tests and four dedicated backend separation tests pass. From the
backend directory, run the integration checks with:

```sh
.venv/bin/python -c "import runpy; runpy.run_path('../project-model/model/integration/check_pricing_separation.py', run_name='__main__')"
```

No backend production behavior changed. See
`requirements/inference/inference-boundaries.md`. UI non-overwrite and full
Manual/Autopilot integration remain later work. Section 5.5 safe fallback or
REVIEW is now complete; structured logging is next (5.6).

## Safe baseline fallback or REVIEW

Failure behavior defaults to REVIEW with no price. Explicit server startup settings
control baseline candidates:

```sh
SFI_PRICING_FALLBACK_MODE=baseline
# Separate opt-in for training-unseen categories:
SFI_PRICING_UNSEEN_CATEGORY_ACTION=baseline
```

`SFI_PRICING_MODEL_BLOCKED=true` disables model loading/execution after an external
reliability/support decision and applies the selected failure policy. Invalid
settings, malformed inputs or unusable fallback artifacts always fail closed.
Restart the backend after changing these settings.

Fallback loading verifies its own baseline/policy/provenance and works without
PyTorch, model weights or the preprocessing pickle. Successful candidates return
`pricing_source: baseline`, `status: fallback_advisory`, `model_version: null`, a
trigger, reference/hashes, and REVIEW/guardrail flags with submission disabled.
Model responses now explicitly identify their model source and the same operational
restrictions. Neither branch authorizes a bid or replaces the dispatcher-entered
amount. Baselines remain frozen training-only references.

All 163 model/API tests, four separation tests, and 24 backend regression tests pass.
Real-backend default-review and opt-in baseline examples are saved in
`artifacts/api/fallback-v1/examples.json`. No deployment settings were changed.
See `requirements/inference/safe-fallback.md`. Structured logging (5.6) is now
complete; Manual Mode integration is next.

## Structured pricing logs

Section 5.6 emits JSON lines on stderr through the dedicated pricing logger.
Each pricing response has a generated `X-Prediction-Id`, matching one completion
event with outcome/status, model/baseline policy versions, latency and safe error/
warning codes. Startup, shutdown and sanitized diagnostic events are also logged.
Concurrent requests retain independent correlation IDs.

Logs exclude raw shipment inputs, bid/cost/margin values, tokens, client IPs,
queries, bodies, paths, and exception messages/tracebacks. Logging-sink failures
cannot change pricing behavior. Existing backend/root logging remains unchanged;
durable operational audit storage is separate later work.

All 171 model/API tests, four backend separation tests and 24 backend regression
tests pass. Verified real-backend examples are in
`artifacts/api/logging-v1/pricing-events.jsonl`. See
`requirements/inference/structured-logging.md`. Section 5 is complete; next is
section 6 Manual Mode integration, now complete as described below. Release
remains unverified and model-driven submission disabled.

## Manual Mode integration

This project exposes `POST /api/v1/manual-mode/evaluate`. Your backend sends the
entered bid, its calculated cost/profit/margin, and shipment features. The service
preserves the manual bid/economics, returns separate advisory pricing and
comparisons, and keeps model inputs free of manual financial values. Model
failures return nested unavailable advice without discarding valid manual context.
It does not recalculate economics, reserve units or submit bids.

Run from this project:

```sh
uv sync --extra api
uv run --extra api uvicorn sfi_model.api.app:app --host 127.0.0.1 --port 8001
```

Open `/docs` for interactive requests or `/openapi.json` for the live schema.
See the [Manual Mode API guide](requirements/docs/api/manual-mode.md),
[OpenAPI specification](requirements/docs/api/openapi.json), and
[JSON request example](requirements/docs/api/examples/manual-mode-request.json) for integration.
The feature-only `POST /api/v1/predict-bid` endpoint remains available unchanged.

Manual Mode also returns `recommended_range`: training-only historical RPM
quartiles converted to loaded-mile dollars, intersected with backend-estimated
cost and supplied minimum-profit/margin thresholds. It reports no feasible range
when policy and historical prices conflict. See
[Historical price range](requirements/docs/api/historical-price-range.md).
The frozen sidecar is `artifacts/baselines/historical-range-v1.json`; deploy it
alongside the model bundle or configure `SFI_HISTORICAL_RANGE_ARTIFACT`.

All 200 model/API tests pass, including 14 Manual Mode contract tests and 17 historical-range checks. A smoke
request against the packaged model preserves a $2,000 manual bid and the supplied
$600/30% economics while returning separate model advice.

This integration pass changes only this model project. External frontend and
backend wiring are consumer-owned; earlier external changes are not reverted.
Autopilot remains disabled and model release remains unverified.

## Live-only Autopilot

Use `POST /api/v1/autopilot/analyze-batch` (or its `/autopilot/live/analyze-batch`
alias) for current orders and candidate trucks. The service returns BID/SKIP,
projected profit, batch-average RPM, historical model comparisons and selected
pairs. Fixed-rate revenue uses `offered_rate_dollars` unchanged; open-bid prices
come from the frozen model or an explicitly configured baseline.

Use `strategy: "fleet_allocation"` to maximize compatible profit across trucks,
or `best_order` for one recommendation. Single-order open bids use
`POST /api/v1/autopilot/evaluate` or `/autopilot/live/evaluate`.

Every Autopilot route is live-only, authenticated and controlled by
`SFI_AUTOPILOT_LIVE_ENABLED`, `SFI_AUTOPILOT_LIVE_TOKEN` and
`SFI_AUTOPILOT_KILL_SWITCH`. No shadow mode, journal/outcome service, shadow-evidence
gate or approval file remains. Configure the shared token and enable the service;
see [live API setup](requirements/docs/api/live-autopilot.md),
[batch contract](requirements/docs/api/batch-profit-analysis.md) and
[complete request](requirements/docs/api/examples/offered-batch-request.json).

`eligible_for_live_submission=true` is preflight eligibility. The backend must
reserve capacity, recheck current state and authorization, and submit idempotently.
The model service never books orders: `submission_enabled=false` and
`backend_revalidation_required=true` remain explicit. Manual pricing is unchanged.

Removing the evidence gate does not certify the frozen model or historical fleet
state. The open-bid-trained reference remains labeled as unvalidated for fixed
rates; time-aware pricing remains pending. Earlier artifacts are historical
records, not current activation requirements. The independent saved-validation
audit remains available; see [decision evaluation](requirements/evaluation/decision-backtesting.md).

For requirement 8, export original live batch requests/responses, submission
attempts and completed actual costs from your backend, then run the offline
`sfi_model.evaluation.live_audit` command. See the
[backend export contract](requirements/docs/api/live-audit-export.md).
This produces an audit report without inference, retraining or automatic data collection.

## Synthetic setup example

```sh
uv run python main.py --epochs 20 --batch-size 128
uv run python main.py --device cpu --epochs 2
```

Automatic device selection prefers CUDA, then Apple MPS, then CPU. You can explicitly
choose `--device cpu`, `--device mps`, or `--device cuda`. The default seed is 42;
results can still vary across devices. Replace the synthetic dataset and model in
`main.py` for your ML task.

The checkpoint at `artifacts/model.pt` contains CPU model weights, architecture
dimensions, seed, epoch count, and final validation accuracy. Set a different path
with `--output path/to/model.pt`. It stores inference weights, not optimizer state
for resuming training.

## Notebooks and code checks

```sh
uv sync --extra notebooks
uv run --extra notebooks jupyter lab
uv run ruff check .
uv run ruff format --check .
```

Keep datasets in `data/` and generated checkpoints in `artifacts/`; both are ignored
by Git. Use `uv add package-name` to add a dependency and update the lockfile.
