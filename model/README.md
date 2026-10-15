# SFI PyTorch workspace

Source code is grouped by domain under `sfi_model/`, with matching test folders:

```text
sfi_model/
  data/          # validation, open-bid preparation, chronological splitting
  features/      # feature schema and shared preprocessing
  inference/     # versioned preprocessing bundle export/loading
  training/      # synthetic PyTorch setup example
  paths.py       # shared project paths
tests/
  data/
  features/
  inference/
requirements/
  data/
  model/
  operations/
  evaluation/
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
