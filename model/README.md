# SFI PyTorch workspace

Source code is grouped by domain under `sfi_model/`, with matching test folders:

```text
sfi_model/
  data/          # validation, open-bid preparation, chronological splitting
  features/      # feature schema and shared preprocessing
  baselines/     # training-only non-ML pricing references
  evaluation/    # validation price comparisons
  inference/     # versioned preprocessing bundle export/loading
  training/      # synthetic PyTorch setup example
  paths.py       # shared project paths
tests/
  data/
  features/
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

## Training

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
