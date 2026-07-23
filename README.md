# Mr Hide

Mr Hide is a local privacy boundary for supported Codex and Claude Code versions. It detects supported PII and technical secrets locally, substitutes detected values before inference, restores known mappings inside the local trust boundary, and stores conversation mappings in encrypted resumable vaults.

Mr Hide preserves OpenAI Responses for Codex and Anthropic Messages for Claude Code. It does not route models or translate protocols.

## Install

Mr Hide requires Python 3.11 or newer. Install the package and the exact English and Spanish spaCy models used by the release-candidate matrix:

```shell
python -m pip install .
python -m pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
python -m pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl
mr-hide doctor
```

The models run in the Mr Hide process; Docker and a separate Presidio service are not required. `doctor` reports only redacted capability state.

## Use

Launcher options must appear before the explicit `--` boundary. Arguments after it are passed to the native client without changing the user's persistent client configuration.

```shell
# New Codex execution
mr-hide codex --upstream https://api.example.test -- exec "Review this repository"

# Explicit Codex resume
mr-hide codex --upstream https://api.example.test -- resume 01234567-89ab-4def-8123-456789abcdef

# New non-interactive Claude Code session
mr-hide claude --upstream https://api.example.test -- -p "Review this repository"

# Explicit Claude Code resume
mr-hide claude --upstream https://api.example.test -- --resume 01234567-89ab-4def-8123-456789abcdef
```

The upstream can be a protocol-compatible provider or another local proxy. Authentication, model routing, and protocol translation remain the upstream's responsibility.

Both client commands support `--tool-policy` with these values:

- `default` protects conversational fields but leaves provider-bound tool definitions, arguments, results, and history unchanged. Mr Hide prints `tool-data-unprotected`.
- `safe-tool-calls` applies compact aliases to eligible conversation and tool data. It may break tools that cannot tolerate substitution.
- `tool-compatibility` uses deterministic realistic PII surrogates and non-working secret stand-ins across eligible conversation and tool data.

`--bypass` requires `--accept-bypass-warning`. Bypass is visible, encrypted in that conversation's vault, and isolated from every other conversation.

## State and retention

Mappings are encrypted with a per-conversation key derived from an installation key held by the approved operating-system keyring. Vaults expire after 30 days of inactivity. Each protected new launch cleans unrelated expired vaults; each successful resume refreshes its selected vault before cleanup runs.

Set `MR_HIDE_STATE_DIR` to an absolute path to choose the state directory. Set `MR_HIDE_KEYRING_SERVICE` only when an isolated keyring identity is required, such as in automated tests. Neither setting is written into native client configuration.

## Privacy boundary

Detection is best effort. Mr Hide guarantees fail-closed handling for supported values it detects; it cannot guarantee discovery of every sensitive value and does not conceal arbitrary source code or all proprietary information. Binary/image content, thinking signatures, unknown protocol structures, authentication, telemetry, update checks, plugin discovery, and non-inference egress remain outside or opaque to the declared privacy matrix.

Run `mr-hide compatibility` for candidate client ranges. Untested versions block by default; `--allow-untested` is a visible one-run override and never expands advertised support.

See [client compatibility](docs/compatibility.md), [traffic boundary](docs/traffic-boundary.md), [privacy core](docs/privacy-core.md), and [release readiness](docs/release-readiness.md) for the versioned evidence and remaining cross-platform gate.

## Development

```shell
python -m pip install "uv==0.11.31"
python -m uv sync --locked --all-extras
python -m uv run --locked python scripts/check_release_readiness.py --fast
python -m uv run --locked python scripts/check_release_readiness.py
```

The full command runs tests, static checks, benchmark/evidence drift, lock validation, build, and clean artifact inspection. It does not publish, tag, push, or dispatch a remote workflow.
