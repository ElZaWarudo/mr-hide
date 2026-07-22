---
title: Executable Privacy Proxy Foundation Work Package
status: in-progress
roadmap_item: RDM-001
origin_roadmap: docs/roadmaps/2026-07-22-001-token-aware-privacy-proxy-roadmap.md
origin_brainstorm: none
origin_planning_input: docs/plans/2026-07-22-001-feat-executable-privacy-proxy-foundation-plan.md
origin_plan: docs/plans/2026-07-22-001-feat-executable-privacy-proxy-foundation-plan.md
units: [U1, U2, U3, U4, U5, U6]
unit_alignment: complete
review_units: [RU1, RU2, RU3]
base_branch: develop
pr_strategy: local-merge
max_open_stack: 0
jira_policy: optional
production_posture: unknown
autonomy: high
autonomous_ledger: none
allowed_mutation_classes: []
---

# Executable Privacy Proxy Foundation Work Package

## Scope

Implement the complete RDM-001 executable foundation: installable Python CLI, evidence-backed Codex and Claude Code adapters, loopback raw-stream proxy, cross-platform process supervision, approved OS-keyring capability proof, real-client compatibility matrix, and boundary documentation.

## Non-goals

- Presidio detection, normalization, reversible aliases, surrogate banks, and privacy transformations.
- Durable conversation mappings, encrypted vault lifecycle, retention, expiry, and bypass persistence.
- Complete OpenAI Responses or Anthropic Messages parity beyond the minimal contract fixtures.
- macOS, additional clients/protocols, routing, protocol translation, prompt compression, or live-provider tests.
- Commits, Jira mutation, pushes, PR creation, reviewer assignment, or merges from the work phase.

## Autonomy Contract

- Mode: high for package-local artifacts, implementation, tests, review fixes, and verification.
- Agent may decide without asking: internal names, equivalent repo-relative layout adjustments, exact dependency patch constraints, fixture payloads, diagnostic structure, test organization, and small implementation details that preserve the plan.
- Agent must record as assumptions: greenfield conventions, compatible library-version adjustments, CI-only verification gaps, and implementation-time discoveries that do not change public behavior.
- Agent must escalate: product behavior, auth/data contracts, weakened key separation, raw fallback after privacy failure, public CLI compatibility breakage, non-loopback exposure, destructive operations, production/deployment policy, branch/base strategy, Jira/PR workflow, credentials, paid external resources, or scope outside RDM-001.
- Safe fallback: continue hermetic implementation, tests, and docs that do not depend on a blocked decision; otherwise record the exact decision and evidence.
- Autonomous ledger: none.
- Allowed external mutation classes: none; executor mode is `manual-required` until Release Marshal validates separate authority.

## Dependencies

- Requires: reviewed `docs/plans/2026-07-22-001-feat-executable-privacy-proxy-foundation-plan.md`.
- Blocks: the RDM-002 reversible privacy/state core and every later roadmap item.
- Internal review-unit order: RU1 → RU2 → RU3. RU3 also requires RU1's secure-store dependency scaffold but receives the complete behavior through RU2's refreshed base.

## Production Posture

- Posture: unknown.
- Evidence: no implementation, releases, deployments, operators, or production data exist in the repository.
- Confidence: high that no production posture is established; low confidence about the eventual deployment environment.
- Consequences for this package: preserve public contracts conservatively, use only synthetic data, keep secure defaults, and require cross-platform evidence before support claims.
- Breaking existing behavior allowed: only with explicit approval; greenfield status does not authorize weakening the accepted Product Contract.

## Plan Unit Alignment

| Plan unit | Included in this package | Reason |
|---|---|---|
| U1 | yes, RU1 | Package/quality foundation is required by every other unit. |
| U2 | yes, RU1 | Client adapters and version policy form one reviewable CLI contract with U1. |
| U3 | yes, RU2 | Raw forwarding is the runtime network boundary. |
| U4 | yes, RU2 | Supervisor and proxy are tightly coupled for executable end-to-end value. |
| U5 | yes, RU3 | Secure-store proof is a dedicated security surface consumed by the support claim. |
| U6 | yes, RU3 | Real-client evidence and docs verify RU1/RU2/U5 as one support envelope. |

Grouping rationale:

- RU1 combines scaffold and adapters because either alone would be a low-value micro-PR; together they deliver an installable CLI that can diagnose clients and enforce version/config contracts with fake binaries.
- RU2 combines proxy and supervisor because the meaningful reviewer outcome is a runnable local round trip with lifecycle cleanup. Splitting them would create two tightly stacked reviews whose tests and core configuration overlap.
- RU3 combines keyring qualification with real-client/CI evidence because it is the support-claim gate: the reviewer sees the secure environment requirement, matrix evidence, and user-facing boundary docs together. Generated evidence must be separated in commit grouping from functional logic.
- No unit is excluded, deferred, or silently moved to another branch.

## Implementation Units

- U1. Package and quality foundation.
- U2. Client adapters and compatibility policy.
- U3. Byte-preserving local forwarding core.
- U4. Cross-platform launch supervisor.
- U5. Secure-store capability proof.
- U6. Real-client compatibility evidence and documentation.

## Review Units

| Review unit | Scope | Expected changed surfaces | Local merge target | Jira | Size/risk note |
|---|---|---|---|---|---|
| RU1 | Installable CLI, client adapters, argument/config isolation, version manifest and diagnostics | package config, CLI, adapters, unit/integration fixtures, base CI | `develop` | omitted by local-only policy | Target 600-850 authored lines; external CLI contracts, no generated docs. |
| RU2 | Loopback raw-stream forwarding and cross-platform supervised process lifecycle | proxy/runtime logic, upstream/fake-client fixtures, integration tests | `develop` after RU1 local merge | omitted by local-only policy | Target 750-1,000 authored lines; size warning accepted because proxy and supervisor verify as one capability. Split by commits for forwarding vs lifecycle/tests. |
| RU3 | Approved keyring proof, pinned real-client matrix, compatibility/egress docs | security capability, system/compatibility tests, workflows, manifest, generated docs | `develop` after RU2 local merge | omitted by local-only policy | Target 650-900 authored lines plus generated evidence; security review required and generated artifacts isolated in commit grouping. |

## Execution Status

| Review unit | Status | Evidence |
|---|---|---|
| RU1 (U1 + U2) | merged-locally | Merged into local `develop` as `06120c9`; no remote mutation occurred. |
| RU2 (U3 + U4) | merged-locally | Merged into local `develop` as `bb9f079`; no remote mutation occurred. |
| RU3 (U5 + U6) | merged-locally | Merged into local `develop` as `8494c90`; no remote mutation occurred. |

Delivery policy: local merges only. Each review unit is committed on its semantic feature branch, rebased onto local `develop`, and merged locally after its gates pass. Do not push branches, create PRs, mutate Jira, notify reviewers, or merge remotely.

## Reviewability Diagnosis

- Reviewer-experience check: yes. Each PR has a semantic outcome and its own verification: client contract, executable runtime, then supported-environment evidence.
- Granularity chosen because: it is the coarsest sequence that keeps CLI contracts, network/process behavior, and security/support evidence understandable without mixing all risks into one diff.
- Integration cadence: merge each passing review unit locally into `develop` before starting the next unit. This preserves review boundaries without creating a PR stack.
- Jira mapping: three review-unit PRs map to one shared Spanish parent with one subtask per RU; each PR backlinks its own subtask. If Jira remains unavailable under optional policy, record omission without blocking.
- Downstream-fix trace: none initially. Any RU2/RU3 change that addresses an open earlier-PR finding must be recorded as `addresses finding from PR #X` in state and handoff notes.
- Failure-mode check: three capability branches with gated local merges avoid both a deep stack and a single unreviewable integration dump.

## Files and Tests

- RU1 runtime: `pyproject.toml`, `uv.lock`, `src/mr_hide/cli.py`, `src/mr_hide/clients/`, `src/mr_hide/compatibility.py`, `src/mr_hide/compatibility.toml`, `src/mr_hide/diagnostics.py`.
- RU1 tests: `tests/unit/test_cli.py`, `tests/unit/test_client_adapters.py`, `tests/unit/test_compatibility.py`, `tests/integration/test_resume_identity.py`.
- RU2 runtime: `src/mr_hide/proxy/`, `src/mr_hide/runtime/`.
- RU2 tests: `tests/unit/test_headers.py`, `tests/integration/test_proxy_passthrough.py`, `tests/integration/test_proxy_streaming.py`, `tests/integration/test_supervisor.py`, `tests/integration/test_concurrent_launches.py`.
- RU3 runtime/evidence: `src/mr_hide/security/`, `tests/compatibility/`, `scripts/compatibility/render_evidence.py`, `.github/workflows/`, `docs/compatibility.md`, `docs/traffic-boundary.md`, `README.md`.
- RU3 tests: `tests/unit/test_keyring_probe.py`, `tests/integration/test_system_keyring.py`, `tests/compatibility/test_codex_contract.py`, `tests/compatibility/test_claude_contract.py`, `tests/compatibility/test_evidence.py`.

## Impact Scan

- Changed API contracts/endpoints/bindings/helpers/schemas/payloads/auth/tenant/ownership/test fixtures: new public CLI; child environment/argv contracts; local loopback Responses/Messages/counting endpoints; compatibility TOML/evidence schema; keyring capability boundary; synthetic fixtures.
- Consumer scan patterns: `rg -n "mr-hide|openai_base_url|ANTHROPIC_BASE_URL|CODEX_HOME|resume|compatibility.toml|keyring|/v1/responses|/v1/messages" .`.
- Consumers found: only current planning/orchestration documents; the repository is greenfield.
- Contract-drift tests searched: exact CLI help/argument behavior, supported-version boundaries, generated-doc drift, route allowlist, hop-by-hop headers, diagnostic sentinel exclusions, approved backend types, and matrix boundary versions.
- Required consumer tests: every test file named above plus README/compatibility command smoke checks.
- Consumer tests run/skipped: RU1 completed with 45 passing tests on lock-resolved Python 3.11.15 and 3.13.7. RU2 completed with 77 hermetic tests on Python 3.11 and 3.13. RU3 completed 87 hermetic core tests on Python 3.11 and 3.13; four exact real-client Windows cells; the actual Windows Credential Locker probe; and 13 focused keyring/evidence tests. Linux system-keyring and real-client cells are defined in SHA-pinned workflows but are not claimed as locally executed.

## Verification Gate

- RU1: editable/wheel install, CLI smoke, adapter/version unit tests, resume seam integration, lint/types/build on Windows/Linux.
- RU2: header/stream unit and integration tests; timeout/disconnect/empty-body cases; fake process group cleanup and concurrent launch isolation on Windows/Linux.
- RU3: weak-backend rejection, approved Windows/Secret Service integration, pinned Codex/Claude matrices, evidence/doc drift, sentinel leak scan, full core suite.
- Surface-aware evidence: public CLI → help/argv/config tests; endpoints/streaming → raw capture tests; process lifecycle → child+descendant/socket assertions; keyring → system integration plus downgrade rejection; docs/manifest → deterministic generation check.
- Production posture evidence: because posture is unknown, no live deployment claim is made; compatibility and security claims require regression evidence on every named OS/version boundary.

## Review Gate

- Code review threshold: P0-P2.
- Findings below threshold: record as advisory unless the user marks them blocking.
- Required review lenses: correctness, maintainability, testing, project standards; add Python, reliability, API-contract, performance, and security lenses by changed surface.

## Security Gate

- Run after work-review loop: required for all three RUs because they handle credentials, external API traffic, subprocesses, public local endpoints, privacy claims, dependencies, and OS key storage.
- Security Watch during work: enabled. Watch header/auth redaction, URL validation, loopback enforcement, ambient proxy bypass, raw-body logging, subprocess injection/cleanup, manifest overrides, keyring downgrade, fixture/artifact leakage, and dependency supply chain.
- Security Watch notes: use synthetic sentinels; never print env values or bodies; no shell interpolation; no non-loopback bind; no file-keyring fallback; no live credentials/providers.
- Security reviewer: `krt-security-sentinel` after code-review fixes.
- Security review result: all three review units passed with no remaining P0-P2 findings. RU3 verifies exact-type backend allowlisting, no fallback, random synthetic credentials, cleanup on every probe path, redacted failures, isolated real-client configuration, dummy provider credentials, no request-body capture, no live-provider dependency, SHA-pinned actions, and explicitly limited support claims. One P2 backend-discovery exception path was fixed and regression-tested.
- Required security verification: diagnostic/evidence sentinel scans, URL/header policy tests, untrusted argv tests, weak-backend rejection, system keyring cleanup, dependency audit where tooling is available.

## CI Break-Prevention And Escalation

- CI risk surfaces: Python 3.11/3.13, Windows/Ubuntu process behavior, Node 22 client installs, npm package pins, D-Bus/Secret Service setup, async streaming timing, generated documentation, lint/type/build constraints.
- Preventive evidence: hermetic tests precede system/compatibility jobs; exact package version is asserted after install; keyring and client jobs are separate; artifacts are deterministic and sentinel-scanned.
- If CI breaks: invoke `krt-ci-questor` with PR/run/check context; Compound Master does not poll checks.
- Escalation rule: do not hand off a CI failure without cause classification, ownership, evidence, and a focused fix or explicit external blocker.

## Local Branch And Merge Inputs

### RU1 Client compatibility foundation

- Review unit: RU1.
- Branch name: `codex/client-compatibility-foundation` (active; created from the common seed at `ba09b20`).
- Branch/docs rule: this first executable RU carries the related roadmap, plan, package, and orchestration state; no planning-only branch.
- Local merge target: `develop`.
- Suggested commit grouping:
  - `feat(cli): establish the client compatibility foundation` — package, CLI, adapters, manifest, diagnostics — one public contract.
  - `test(cli): prove client argument and version boundaries` — unit/fake-client/resume tests — reviewable evidence.
- Local merge summary: `feat: establish the client compatibility foundation`.
- Change summary: installable CLI and native-state-safe adapters; tested-version enforcement; synthetic verification and current scope limitations.
- Verification results location: package Verification Gate plus Compound Master state.
- Production/deployment notes: no deployment; production posture unknown.
- Autonomous mutation request: none.

### RU2 Local proxy runtime

- Review unit: RU2.
- Branch name: `feat/local-streaming-proxy-runtime`.
- Local merge target: `develop` after RU1 is integrated.
- Suggested commit grouping:
  - `feat(proxy): forward declared inference streams on loopback` — proxy/routes/headers/stream tests.
  - `feat(runtime): supervise local client and proxy lifecycles` — runtime/process/diagnostic logic and lifecycle tests.
- Local merge summary: `feat: add the supervised local proxy runtime`.
- Change summary: raw declared-route forwarding; cross-platform process-group cleanup; concurrent launch isolation and failure evidence.
- Verification results location: package Verification Gate plus Compound Master state.
- Production/deployment notes: local-only runtime; no deployment.
- Autonomous mutation request: none.

### RU3 Cross-platform compatibility evidence

- Review unit: RU3.
- Branch name: `feat/cross-platform-compatibility-evidence`.
- Local merge target: `develop` after RU2 is integrated.
- Suggested commit grouping:
  - `feat(security): require an approved operating-system keyring` — capability code and downgrade/system tests.
  - `test(compatibility): verify supported clients across platforms` — client harness/workflows/evidence tests.
  - `docs(compatibility): publish tested boundaries and egress limits` — generated evidence and operator docs.
- Local merge summary: `feat: prove the supported cross-platform boundary`.
- Change summary: approved keyring capability; pinned real-client matrix; reproducible support and egress documentation.
- Verification results location: package Verification Gate plus Compound Master state.
- Production/deployment notes: release support evidence only; no production deployment.
- Autonomous mutation request: none.

## Jira Handoff Inputs

- Jira policy: optional.
- Suggested issue type: parent `Tarea` plus one subtask per RU because three sibling review units share one capability.
- Suggested parent summary: `Establecer la base ejecutable del proxy de privacidad`.
- Suggested parent description: `Crear la base instalable y verificable que permita ejecutar Codex y Claude Code a través de un proxy local sin alterar su configuración persistente ni adelantar las transformaciones de privacidad.`
- RU1 summary: `Preparar la compatibilidad y configuración aislada de los clientes`.
- RU1 description: `Añadir la CLI instalable, los adaptadores de Codex y Claude Code, el control de versiones probadas y las pruebas de argumentos, configuración y reanudación.`
- RU2 summary: `Construir el runtime local de streaming y supervisión`.
- RU2 description: `Implementar el proxy loopback que conserva bytes y el ciclo de vida multiplataforma del cliente y del servidor con limpieza segura.`
- RU3 summary: `Demostrar el soporte seguro y multiplataforma`.
- RU3 description: `Validar los keyrings aprobados, ejecutar clientes reales fijados por versión y publicar evidencia reproducible de compatibilidad y límites de tráfico.`
- PR-to-Jira mapping: each RU remains one subtask and one PR; backlink and transition only the subtask delivered by that PR, with the shared parent completed after all three.
- Optional-policy fallback: Jira omitted if role/context/config needed for safe mutation is unavailable; continue without asking solely whether Jira matters.
