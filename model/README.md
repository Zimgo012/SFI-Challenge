# SFI PyTorch workspace

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
