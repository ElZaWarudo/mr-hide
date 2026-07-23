---
roadmap_item: RDM-004
plan: docs/plans/2026-07-22-004-feat-claude-anthropic-messages-protection-plan.md
status: ready
integration_base: develop
delivery: local-only
review_units: [RU1, RU2]
review_threshold: P0-P2
---

# Claude Anthropic Messages Work Package

## Scope

Protect the exact Anthropic Messages JSON/SSE and token-counting surfaces used by supported Claude Code versions, then bind new and explicitly resumed sessions to the encrypted conversation lifecycle and all three tool policies.

## Non-goals

- No OpenAI translation, model routing, generic recursive JSON rewriting, live provider call, or unsupported Anthropic endpoint parity.
- No support claim for ambiguous Claude session picker, name, or `--continue` identity forms.
- No claim that default provider-bound tool data is protected.

## Autonomy Contract

- The initiative brief, roadmap, and reviewed RDM-002/RDM-003 behavior are authoritative.
- Escalate only if pinned Claude behavior requires weakening explicit session binding, fail-closed processing, or the accepted tool policies.
- Local branches, commits, rebases, and `--no-ff` merges into `develop` are authorized. Pushes, PRs, Jira changes, and remote merges are prohibited.

## Dependencies

- RDM-001 through RDM-003 are locally integrated in `develop` at `af00f04` or later.
- RU order is strict: RU1 then RU2.
- Messages protocol types must not leak into the shared privacy transaction or Responses protocol module.

## Review Units

| Review unit | Plan units | Outcome | Branch | Local merge target |
|---|---|---|---|---|
| RU1 | U1 | Pure bounded Messages/count JSON and SSE transformations preserve unknown protocol data and enforce policy without a network runtime. | `codex/anthropic-messages-protection` | `develop` |
| RU2 | U2 | Supported Claude launch/resume traffic uses bound encrypted conversations end to end with reviewed cross-protocol evidence. | `codex/claude-messages-runtime` | `develop` after RU1 |

## Execution Status

| Review unit | Status | Evidence |
|---|---|---|
| RU1 | merged-local | Strict bounded Messages/count JSON and SSE transforms passed 23 focused tests, 66 cross-protocol tests, Python 3.13 (314 passed, 1 skipped), Python 3.11 (309 passed, 1 skipped), Ruff, strict mypy, build, and clean-wheel smoke; merged locally as `de592d9`. |
| RU2 | ready-local-merge | Provider-neutral transactions, launcher-owned Claude UUID binding, protected Messages/count routing, policy/bypass parity, generated evidence, and isolated real Claude 2.1.216/2.1.217 launch/resume contracts pass. Python 3.13: 332 passed, 3 skipped; Python 3.11: 325 passed, 1 skipped, 9 deselected. |

## Reviewability Diagnosis

- RU1 is independently demonstrable with pure protocol fixtures and no keyring, subprocess, socket, or provider.
- RU2 owns shared-transaction extraction, identity binding, proxy/CLI composition, real-client contracts, generated evidence, and final leakage assertions.
- The split isolates parser/security review from process/session behavior while preserving one coherent Claude capability.

## Files and Tests

- RU1 runtime: `src/mr_hide/protocols/messages/` only.
- RU1 tests: `tests/protocols/messages/` with JSON, count, SSE, policy, unknown-preservation, bounds, and leakage fixtures.
- RU2 runtime: `src/mr_hide/runtime/privacy.py`, Claude adapter/CLI, proxy handlers/routes, and binding integration.
- RU2 tests: lifecycle/binding, proxy Messages/count, pinned Claude compatibility, wheel/docs/evidence checks.

## Verification Gate

- Pure tests cover every declared path/event and all three policies, including duplicate/truncated/oversized input and arbitrary SSE boundaries.
- End-to-end tests prove blocked traffic never calls upstream and eligible originals are absent from captured protected traffic.
- Run Python 3.11/3.13, Ruff, strict mypy, dependency audit, build, clean-wheel smoke, pinned Claude Windows evidence, workflow YAML, generated-doc drift, and sentinel scans.

## Review Gate

- Run simplification before review.
- Required lenses: correctness, maintainability, testing, project standards, Python, reliability, performance, data integrity, API contracts, streaming races, security, and adversarial parser/session construction.
- Fix every confirmed P0-P2 before each local merge.

## Security Gate

- Watch duplicate keys, recursive overreach, raw fallback, partial SSE disclosure, unbounded buffers, malicious indices, partial tool JSON differentials, cross-conversation restoration, session-name/path traversal, ambiguous resume forms, stale state, and source text in errors/logs.
- Unknown content remains opaque; unsupported eligible structures block rather than pass through.

## CI Break Prevention

- Preserve the protected Responses path while RU1 adds pure Messages transformers.
- Use protocol-shaped local Messages/count responses and exact Claude packages; never require live credentials.
- Keep hermetic protocol tests separate from real-client/keyring compatibility jobs.

## Branch and PR Handoff Inputs

The handoff is local-only. PR metadata is omitted; each passing review unit is rebased and merged locally.

- Selected Review unit: RU1 Anthropic Messages protocol transformers.
- Review summary: explicit field/event matrix, bounded strict parsing, count parity, all policy modes, unknown preservation, and fail-before-forward behavior.
- PR body bullets retained only as checker-compatible local review metadata:
  - Summary: transform only declared Anthropic Messages text/tool fields and preserve unknown protocol data.
  - Verification: bounded JSON/SSE adversarial fixtures, count parity, policies, Python matrix, lint, types, audit, build, and wheel smoke.
  - Risk: malformed or unsupported eligible structures block; unknown opaque structures are preserved without recursive rewriting.

### RU1 Messages protocol transformers

- Suggested commits: strict JSON/count matrix; SSE transformer; adversarial fixtures and review fixes.
- Merge summary: `merge: integrate Anthropic Messages protocol transformers`.

### RU2 Claude Messages runtime

- Suggested commits: shared transaction extraction; native session binding; proxy/CLI composition; compatibility/evidence closure.
- Merge summary: `merge: integrate protected Claude Messages runtime`.

Delivery policy: rebase each passing branch onto local `develop`, merge with `--no-ff`, retain semantic branches locally, and perform no remote mutation.
