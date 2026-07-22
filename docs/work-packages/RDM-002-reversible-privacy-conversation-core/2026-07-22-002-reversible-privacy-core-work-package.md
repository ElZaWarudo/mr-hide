---
roadmap_item: RDM-002
plan: docs/plans/2026-07-22-002-feat-reversible-privacy-conversation-core-plan.md
status: ready
integration_base: develop
delivery: local-only
review_units: [RU1, RU2, RU3]
review_threshold: P0-P2
---

# Reversible Privacy and Conversation Core Work Package

## Scope

Implement the complete provider-neutral RDM-002 privacy core: multilingual Presidio detection, technical-secret recognizers, stable reversible aliases, compatibility surrogates, authenticated encrypted conversation state, retention, bypass, and tool-policy domain behavior.

## Non-goals

- No OpenAI Responses or Anthropic Messages payload traversal.
- No client-native session binding or provider calls.
- No runtime model downloads, remote recognizers, dashboards, deployment, or release claim.
- No guarantee that automated detection finds every sensitive value.

## Autonomy Contract

- The accepted initiative and RDM-002 plan settle product behavior. Implementation may choose internal names and refactor seams without asking.
- Escalate only if evidence requires weakening fail-closed behavior, key separation, 30-day retention, three tool policies, supported languages, or the local-only delivery policy.
- Local branches, commits, rebases, and `--no-ff` merges into `develop` are authorized. Pushes, PRs, Jira changes, and remote merges are prohibited.

## Dependencies

- RDM-001 is locally integrated in `develop` at `448d96f`.
- RU order is strict: RU1 → RU2 → RU3.
- RDM-003 and RDM-004 consume the stable contracts produced here.

## Review Units

| Review unit | Plan units | Outcome | Branch | Local merge target |
|---|---|---|---|---|
| RU1 | U1 + U2 | Text becomes stable reversible compact aliases or compatibility surrogates under tested detection and collision rules. | `codex/privacy-transformation-core` | `develop` |
| RU2 | U3 | Mapping state survives restart through authenticated encryption, approved-keyring separation, atomic persistence, and concurrency control. | `codex/encrypted-conversation-vault` | `develop` after RU1 |
| RU3 | U4 + U5 | Resume/expiry/bypass/tool policies compose safely and the installable package carries cross-platform evidence. | `codex/privacy-policy-lifecycle` | `develop` after RU2 |

## Execution Status

| Review unit | Status | Evidence |
|---|---|---|
| RU1 | integrated | Merged locally into `develop` as `04a283f` after implementation, review, and verification passed. |
| RU2 | integrated | Merged locally into `develop` as `cdd5c7c` after AES-GCM/HKDF/keyring/atomic-repository implementation, review, and verification passed. |
| RU3 | ready-local-merge | Lifecycle/policy/evidence implementation and review passed: 236 tests on Python 3.13 including bilingual models and Windows keyring, 231 hermetic tests on Python 3.11, lint, types, benchmark, YAML, build, and clean-wheel public API smoke. |

## Reviewability Diagnosis

- RU1 is independently demonstrable with pure transformation fixtures and no persistent state.
- RU2 isolates the security-critical storage/key/concurrency surface for focused review.
- RU3 composes lifecycle and policies only after both foundations are stable, then closes packaging evidence.
- The split prevents protocol work from leaking into RDM-002 and keeps each local merge bisectable.

## Files and Tests

- RU1 runtime: `src/mr_hide/privacy/`, `src/mr_hide/config/recognizers.py`, `src/mr_hide/data/`.
- RU1 tests: `tests/privacy/test_detection.py`, `test_recognizers.py`, `test_overlap.py`, `test_aliases.py`, `test_surrogates.py`, `test_round_trip.py`.
- RU2 runtime: `src/mr_hide/state/keys.py`, `codec.py`, `store.py`, `repository.py`, state models.
- RU2 tests: `tests/state/test_codec.py`, `test_store.py`, `test_repository.py`, `tests/security/test_vault_leakage.py`.
- RU3 runtime: lifecycle/bypass services, `src/mr_hide/policy.py`, CLI diagnostics, package/CI/docs/benchmark changes.
- RU3 tests: `tests/state/test_lifecycle.py`, `tests/privacy/test_policy.py`, system keyring/vault tests, build/evidence checks.

## Verification Gate

- Unit/property tests cover normalization, overlap, collisions, Unicode, bank exhaustion, round trips, tamper, wrong identity/key, stale writes, expiry, and bypass isolation.
- Presidio integration uses pinned English and Spanish models locally; missing models prove fail-closed startup.
- Windows and Linux-compatible file behavior runs in the core matrix; approved system keyring coverage remains isolated.
- Run Python 3.11 and 3.13 suites, Ruff, strict mypy, dependency audit, build, clean-wheel smoke, benchmark/doc drift, and sentinel scans.

## Review Gate

- Run simplification before review.
- Required lenses: correctness, maintainability, testing, project standards, Python, reliability, performance, data integrity, API contracts, and adversarial failure construction.
- Fix all confirmed P0-P2 findings and add regression tests before local merge.

## Security Gate

- Required for every RU.
- Watch for plaintext originals/fingerprints, unsafe regexes, ambiguous mappings, weak randomness, nonce reuse, unauthenticated metadata, file permission/atomicity gaps, keyring downgrade, path traversal, rollback/lost updates, expiry races, and fail-open seams.
- Evidence must show errors/logs/artifacts contain reason codes only and that a copied data directory cannot reveal originals without the OS-held key.

## CI Break Prevention

- Pin all project dependencies in `uv.lock` and all CI actions by SHA.
- Keep hermetic core tests separate from model and system-keyring tests.
- Cache or install exact NLP model artifacts in CI without runtime auto-download.
- A failed external model/package download is infrastructure failure, never a reason to weaken protected runtime behavior.

## Branch and PR Handoff Inputs

The checker-compatible handoff is intentionally local-only: each branch has a merge input, while PR title/body/URL and remote publication are omitted by the user-authorized delivery policy.

- Selected Review unit: RU1 Privacy transformation core.
- PR body bullets retained only as local review metadata:
  - Summary: detect English/Spanish PII and technical secrets locally, then assign stable reversible substitutes.
  - Verification: focused privacy tests, Python 3.11/3.13 core suite, lint, types, dependency audit, and security review.
  - Risk: recognizer gaps remain best effort; known processing failures block rather than disclose raw text.

### RU1 Privacy transformation core

- Suggested commits: detector/recognizers; mapping/allocators; round-trip tests and fixtures.
- Merge summary: `merge: integrate reversible privacy transformations`.

### RU2 Encrypted conversation vault

- Suggested commits: key/codec; atomic repository/concurrency; security regressions.
- Merge summary: `merge: integrate encrypted conversation vault`.

### RU3 Privacy policy lifecycle

- Suggested commits: lifecycle/bypass/policy; packaging/CI; evidence/docs/review fixes.
- Merge summary: `merge: integrate privacy policy lifecycle`.

Delivery policy: rebase each passing branch onto local `develop`, merge with `--no-ff`, retain semantic branches locally, and perform no remote mutation.
