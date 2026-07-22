---
roadmap_item: RDM-003
plan: docs/plans/2026-07-22-003-feat-codex-openai-responses-protection-plan.md
status: ready
integration_base: develop
delivery: local-only
review_units: [RU1, RU2]
review_threshold: P0-P2
---

# Codex OpenAI Responses Work Package

## Scope

Protect the exact OpenAI Responses JSON/SSE surfaces used by supported Codex versions, then bind new/resumed native Codex sessions to the RDM-002 conversation lifecycle and all three tool policies.

## Non-goals

- No Anthropic Messages handling or protocol translation.
- No generic recursive JSON rewriting, model routing, provider token API, live provider test, or unsupported OpenAI endpoint parity.
- No claim that default provider-bound tool data is protected.

## Autonomy Contract

- The initiative brief, roadmap, and reviewed RDM-002 policy behavior are authoritative.
- Escalate only if pinned Codex behavior requires broadening undeclared routes, weakening fail-closed processing, or changing the accepted tool policies.
- Local branches, commits, rebases, and `--no-ff` merges into `develop` are authorized. Pushes, PRs, Jira changes, and remote merges are prohibited.

## Dependencies

- RDM-001 and RDM-002 are locally integrated in `develop` at `89b9487` or later.
- RU order is strict: RU1 then RU2.
- RDM-004 remains independent and must not depend on Responses-specific types.

## Review Units

| Review unit | Plan units | Outcome | Branch | Local merge target |
|---|---|---|---|---|
| RU1 | U1 | Pure bounded Responses JSON/SSE transformations preserve unknown protocol data and enforce policy without a network runtime. | `codex/responses-protocol-transformers` | `develop` |
| RU2 | U2 + U3 | Supported Codex launch/resume traffic uses bound encrypted conversations end to end with reviewed evidence. | `codex/codex-responses-runtime` | `develop` after RU1 |

## Execution Status

| Review unit | Status | Evidence |
|---|---|---|
| RU1 | selected | Starts after artifact review and checker pass. |
| RU2 | pending | Starts after RU1 local merge. |

## Reviewability Diagnosis

- RU1 is independently demonstrable with pure JSON/SSE fixtures and no keyring, subprocess, socket, or provider.
- RU2 owns state binding, CLI/runtime wiring, real-client contracts, and the final end-to-end leakage assertions.
- The split keeps parser/security review separate from process/session behavior while delivering one coherent Codex capability.
- Generated compatibility/evidence outputs remain in RU2 with the runtime behavior they attest; they are mechanically checked and do not obscure RU1 parser review.

## Files and Tests

- RU1 runtime: `src/mr_hide/protocols/responses/` and protocol-neutral transformer ports only when shared without provider types.
- RU1 tests: `tests/protocols/responses/` with JSON, SSE, policy, unknown-preservation, bounds, and leakage fixtures.
- RU2 runtime: `src/mr_hide/state/bindings.py`, proxy/runtime composition, Codex adapter/CLI options.
- RU2 tests: binding/lifecycle integration, proxy Responses tests, pinned Codex compatibility, wheel/docs/evidence checks.

## Verification Gate

- Pure tests cover every declared path/event and all three policies, with duplicate/truncated/oversized input and arbitrary SSE chunk boundaries.
- End-to-end tests prove blocked requests never call upstream and original sentinels are absent from protected captured traffic.
- Run Python 3.11 and 3.13 suites, Ruff, strict mypy, dependency audit, build, clean-wheel smoke, pinned Codex Windows evidence, workflow YAML, and sentinel scans.

## Review Gate

- Run simplification before review.
- Required lenses: correctness, maintainability, testing, project standards, Python, reliability, performance, data integrity, API contracts, streaming races, security, and adversarial parser construction.
- Fix every confirmed P0-P2 before each local merge.

## Security Gate

- Watch for duplicate JSON keys, recursive overreach, raw fallback, partial SSE disclosure, unbounded buffers, cross-conversation restoration, resume-identity path traversal, stale state, forged event indices, tool JSON parser differentials, and source text in errors/logs.
- Unknown content remains opaque; unsupported eligible structures block rather than pass through.

## CI Break Prevention

- Preserve the existing raw Anthropic routes and RDM-001 forwarding tests throughout RU1.
- Use captured/synthetic Responses fixtures and exact Codex packages; never require live credentials.
- Keep hermetic protocol tests separate from real-client compatibility jobs.

## Branch and PR Handoff Inputs

The handoff is local-only. PR metadata is omitted; each passing review unit is rebased and merged locally.

- Selected Review unit: RU1 Responses protocol transformers.
- Review summary: explicit field/event matrix, bounded strict parsing, three policies, unknown preservation, and fail-before-forward behavior.
- PR body bullets retained only as checker-compatible local review metadata:
  - Summary: transform only declared OpenAI Responses text/tool fields and preserve unknown protocol data.
  - Verification: bounded JSON/SSE adversarial fixtures, all policy modes, Python matrix, lint, types, audit, build, and wheel smoke.
  - Risk: malformed or unsupported eligible structures block; unknown opaque structures are preserved without recursive rewriting.

### RU1 Responses protocol transformers

- Suggested commits: strict JSON matrix; incremental SSE transformer; adversarial fixtures and review fixes.
- Merge summary: `merge: integrate Responses protocol transformers`.

### RU2 Codex Responses runtime

- Suggested commits: conversation binding; proxy/CLI composition; compatibility/evidence closure.
- Merge summary: `merge: integrate protected Codex Responses runtime`.

Delivery policy: rebase each passing branch onto local `develop`, merge with `--no-ff`, retain semantic branches locally, and perform no remote mutation.
