---
roadmap_item: RDM-005
status: implementation-ready
date: 2026-07-22
integration_base: develop
delivery: local-only
---

# Harden and package the cross-platform MVP

## Objective

Turn the locally integrated Codex and Claude capabilities into an honestly documented release candidate: installable artifacts, automatic retention housekeeping, one cross-client acceptance contract, and generated readiness evidence that distinguishes local Windows results from required Linux CI.

## Accepted behavior

- A standard wheel/sdist install exposes both entry points, packaged compatibility data, typed public modules, and clear exact-model installation instructions without Docker or a separate Presidio service.
- Every protected launch performs bounded global retention cleanup before preparing its conversation. Cleanup revalidates each candidate under its vault lock and fails closed on repository/key errors.
- Codex and Claude preserve existing user configuration, native session identity, upstream composition, all three tool policies, explicit bypass, and provider-specific unknown data.
- Release evidence never upgrades a candidate range merely because local Windows cells passed. Windows/Linux compatibility remains required, and locally unexecuted Linux cells remain visibly pending.
- No release publication, tag, push, PR, remote workflow run, or support-range expansion occurs in this local-only package.

## Requirements

- R5.1. Replace stale early-stage documentation with an operator path covering installation, exact English/Spanish models, both clients, new/resume examples, policies, bypass, upstream composition, retention, diagnostics, supported versions, and explicit privacy limits.
- R5.2. Run `ConversationService.cleanup_expired()` before every new/resumed protected runtime and convert cleanup failures to stable source-free runtime reasons. Do not delete active or concurrently refreshed vaults.
- R5.3. Prove cleanup is invoked for both providers, expires unrelated stale vaults, preserves active vaults, and blocks launch safely when enumeration/decryption/deletion fails.
- R5.4. Add one cross-client acceptance matrix over Responses and Messages/count for default, safe-tool-calls, and tool-compatibility, including protected sentinels, provider-bound default tool exposure, restored output, bypass isolation, malformed fail-before-upstream, unknown preservation, and a composed upstream base path/query.
- R5.5. Validate configuration preservation and launcher-owned native identity for both client adapters without editing native configuration directories or parent environments.
- R5.6. Harden package metadata and distribution inspection: include the license/readme, compatibility manifest, `py.typed`, public protocol/runtime modules, scripts required by source verification, and exclude vaults, credentials, temporary clients, build directories, and local state.
- R5.7. Keep the Windows/Linux Python, NLP-model, system-keyring, and exact-client workflow matrix SHA-pinned and mechanically consistent with the manifest. Add a single release-readiness command that checks generated docs, workflow YAML, lock state, benchmark, tests, build, and wheel contents without publishing.
- R5.8. Generate a durable release-readiness report from versioned evidence inputs. It must list local passes, CI-required cells, privacy/tool limitations, distribution commands, and a conditional verdict rather than claiming unobserved Linux success.

## Technical design

- `src/mr_hide/runtime/privacy.py`: invoke locked retention cleanup before conversation create/resume and expose only stable `PrivacyRuntimeError` reasons.
- `tests/acceptance/test_mvp_matrix.py`: protocol-shaped local upstream matrix spanning both clients and policies with captured-traffic leakage assertions.
- `tests/state/` and protocol handler tests: automatic cleanup, concurrency revalidation, and failure regressions.
- `scripts/check_release_readiness.py`: read-only local orchestrator for deterministic checks with explicit fast/full modes and stable summary output.
- `scripts/verify_wheel.py`: assert the final public modules/resources and absence of forbidden local artifacts.
- `pyproject.toml`, `LICENSE`, `README.md`, and `docs/release-readiness.md`: distribution and operator closure.

## Implementation unit

### U1. Cross-platform MVP hardening and readiness

- Implement automatic cleanup, the cross-client acceptance matrix, package metadata/content checks, read-only readiness command, updated operator documentation, and conditional generated evidence.
- Verify Python 3.11/3.13, Ruff, strict mypy, locked dependency audit, benchmark, workflow/manifest alignment, generated-doc drift, sdist/wheel, clean-wheel smoke, exact Windows client contracts, sentinel scans, and work-package checker.

## Review and security gates

- Correctness: cleanup timing cannot refresh/delete the wrong vault; count responses remain non-mutating; each policy matches both protocols; package assertions match built artifacts.
- Reliability: readiness commands clean temporary output on failure, subprocesses have timeouts, workflows are deterministic, and no network/live-provider dependency enters hermetic tests.
- Security: release artifacts contain no vault/key/state/client cache; readiness output contains no bodies, mappings, credentials, or exception payloads; failed cleanup or acceptance never falls back to raw forwarding.
- Scope: no new protocol, UI, admin plane, telemetry, release publication, macOS claim, or guaranteed-detection language.
- Review threshold: fix every confirmed P0-P2 before the local merge.

## Verification contract

RDM-005 is locally complete when the wheel/sdist and operator path describe the integrated behavior; automatic cleanup and the unified matrix pass on Python 3.11/3.13; exact Windows Codex/Claude evidence remains captured; all required Linux cells are encoded and reported as pending local observation; and the release-readiness command returns a conditional local-pass verdict without mutating remotes.

