---
roadmap_item: RDM-005
plan: docs/plans/2026-07-22-005-chore-cross-platform-mvp-hardening-plan.md
status: merged-local
integration_base: develop
delivery: local-only
review_units: [RU1]
review_threshold: P0-P2
---

# Cross-platform MVP Hardening Work Package

## Scope

Close the release-candidate operational, packaging, acceptance, and evidence gaps across the already integrated privacy core, Codex Responses path, and Claude Messages path.

## Non-goals

- No PyPI/GitHub release, tag, push, PR, remote workflow dispatch, Jira mutation, macOS support, new protocol/client, UI, centralized administration, or guaranteed detection claim.
- No support-status promotion from locally observed Windows evidence alone.

## Autonomy Contract

- The initiative brief, roadmap, integrated RDM-001 through RDM-004 behavior, and this reviewed plan are authoritative.
- Escalate only if hardening requires weakening fail-closed behavior, explicit session binding, policy semantics, or the honest Windows/Linux evidence boundary.
- Local commits, rebase, and one `--no-ff` merge into `develop` are authorized. Pushes, PRs, Jira changes, tags, publication, and remote merges are prohibited.

## Dependencies

- RDM-003 and RDM-004 are locally integrated in `develop` at `7fcfa47` or later.
- Existing lock, workflow, privacy, protocol, and compatibility contracts remain authoritative unless a confirmed release blocker requires a reviewed correction.

## Review Units

| Review unit | Plan units | Outcome | Branch | Local merge target |
|---|---|---|---|---|
| RU1 | U1 | Installable artifacts, automatic retention housekeeping, unified cross-client acceptance, operator guidance, and conditional release-readiness evidence agree on one release-candidate behavior. | `codex/cross-platform-mvp-hardening` | `develop` |

## Execution Status

| Review unit | Status | Evidence |
|---|---|---|
| RU1 | ready-local-merge | Automatic cleanup, bounded vault enumeration, the 13-case cross-client acceptance matrix, workflow YAML, conditional generated evidence, dependency audit, build, archive inspection, and clean-wheel smoke passed. Python 3.13 passed 348 tests with three expected skips; hermetic Python 3.11 passed 341 with one expected skip and nine opt-in deselections. Exact Windows Codex 0.144.4 and Claude Code 2.1.217 launch/resume contracts passed after the runtime change. Inline correctness, maintainability, testing, standards, Python, reliability, performance, data-integrity, package-contract, race, security, and adversarial evidence review found no remaining P0-P2 issue. |

## Reviewability Diagnosis

- The work is one release-readiness claim: splitting documentation/package checks from the acceptance matrix would permit either half to appear shippable without the other.
- Runtime mutation is limited to invoking the already reviewed retention service; the remaining work is tests, deterministic tooling, metadata, and documentation.

## Files and Tests

- Runtime: `src/mr_hide/runtime/privacy.py` only unless review finds a proven cleanup defect in the existing state layer.
- Acceptance: `tests/acceptance/`, focused protocol/state regressions, compatibility evidence assertions.
- Delivery: `README.md`, `LICENSE`, `pyproject.toml`, `scripts/check_release_readiness.py`, `scripts/verify_wheel.py`, generated evidence, and CI consistency checks.

## Verification Gate

- Python 3.11/3.13 full hermetic suites; exact Windows client contracts; both tool policies plus default/bypass/failure/composition acceptance; NLP/keyring gates where locally available.
- Ruff, strict mypy, lock validation, dependency audit, benchmark, workflow YAML, generated evidence, sdist/wheel build, clean-wheel smoke, artifact sentinel scan, and work-package checker.
- Linux workflow cells must be encoded and reported, not falsely claimed as locally run.

## Review Gate

- Run simplification before review.
- Required lenses: correctness, maintainability, testing, project standards, Python, reliability, performance, data integrity, API/package contracts, process races, security, and adversarial release-evidence construction.
- Fix every confirmed P0-P2 before the local merge.

## Security Gate

- Watch cleanup races, unrelated corrupt vaults, stale binding records, source-bearing failures, bypass cross-contamination, default-tool overclaims, package inclusion of state/secrets, shell injection in readiness commands, unbounded subprocess output, and false Linux/support assertions.

## CI Break Prevention

- Preserve SHA-pinned actions, locked resolution, Windows/Linux matrices, exact client packages, isolated keyring services, and no-live-provider fixtures.
- The readiness script is read-only except for validated workspace-local temporary build output and must not invoke remote publication or workflow APIs.

## Branch and PR Handoff Inputs

The handoff is local-only. PR metadata is omitted; the passing unit is rebased and merged locally.

- Selected Review unit: RU1 cross-platform MVP hardening and readiness.
- Review summary: automatic cleanup, unified acceptance, package integrity, operator usability, and evidence honesty.
- PR body bullets retained only as checker-compatible local review metadata:
  - Summary: close operational and distribution gaps without expanding the supported product boundary.
  - Verification: Python/OS/client matrices, policies, cleanup, failure/bypass, composition, lint, types, audit, benchmark, build, wheel, and evidence drift.
  - Risk: cleanup and readiness failures block or report conditional status; no raw fallback or unsupported release assertion.

### RU1 Cross-platform MVP hardening

- Suggested commits: automatic retention cleanup; cross-client acceptance matrix; package/readiness tooling; operator and evidence closure.
- Merge summary: `merge: integrate cross-platform MVP hardening`.

Delivery policy: rebase the passing branch onto local `develop`, merge with `--no-ff`, retain the semantic branch locally, and perform no remote mutation.

## Local Merge Result

RU1 was rebased onto local `develop` and merged with `--no-ff` as `852d6b2`. The semantic branch remains local. No push, PR, Jira mutation, tag, publication, reviewer notification, or remote merge occurred.
