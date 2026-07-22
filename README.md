# Mr Hide

Mr Hide is an early-stage, local privacy boundary for supported coding clients.
The current foundation validates client compatibility and preserves native client
configuration; it does **not** yet transform or protect prompt traffic.

## Development

Mr Hide requires Python 3.11 or newer.

```shell
python -m pip install "uv==0.11.31"
python -m uv sync --locked --all-extras
python -m uv run --locked python -m pytest -m "not compatibility and not system_keyring"
python -m uv run --locked python -m ruff check .
python -m uv run --locked python -m mypy src
python -m uv run --locked python -m build
python -m uv run --locked python scripts/verify_wheel.py dist
```

An ordinary `python -m pip install -e ".[dev]"` remains supported, but the
lock-driven commands above reproduce CI dependency resolution.

The command can be invoked as either `mr-hide` or `python -m mr_hide`.
Launcher-owned options and native client arguments have an explicit boundary:

```shell
mr-hide codex --upstream https://api.example.test -- resume SESSION_ID
mr-hide claude --upstream https://api.example.test -- --resume SESSION_ID
```

Run `mr-hide compatibility` for the candidate client ranges and evidence state.
An untested client blocks by default; `--allow-untested` is a visible, one-run
override and never changes the packaged compatibility manifest.
