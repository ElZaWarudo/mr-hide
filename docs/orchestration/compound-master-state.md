---
initiative: token-aware-privacy-proxy
mode: full
status: in-progress
date: 2026-07-22
production: unknown
jira_policy: optional
parallel: false
delegation: inline
autonomy: high
worktree_policy: avoid
pr_granularity: auto
review_threshold: P0-P2
---

# Compound Master State

## Current Phase

- Phase: RDM-002 RU3 local release gate
- Result: RDM-001 and RDM-002 RU1-RU2 are locally integrated. RDM-002 RU3 implementation, verification, code review, security review, build, and clean-wheel smoke passed on `codex/privacy-policy-lifecycle`; local integration is the remaining RU3 step.
- Primary artifact: `docs/plans/2026-07-22-002-feat-reversible-privacy-conversation-core-plan.md`
- Artifact classification: `implementation-ready unified code plan`

## Preflight

- Workspace: `C:/Users/Mayor/Documents/Caribbean/mr-hide`
- Git repository: yes; remote `origin` is configured
- Integration base: local `develop` at `cdd5c7c`, created from the matching `origin/master` seed and advanced only through local feature merges; it has no upstream
- Active implementation branch: `codex/privacy-policy-lifecycle`, created from local `develop` after the RDM-002 RU2 merge
- Working tree before RU3: clean at `cdd5c7c`; the current diff is limited to lifecycle/policy/evidence closure
- Repo instructions: user-supplied `AGENTS.md` compatibility instructions are active for this session; no repository `AGENTS.md` file exists
- Production posture: `unknown`; no deployment or production evidence exists
- Jira posture: optional; `JIRA_HOST`, `JIRA_API_TOKEN`, and `JIRA_PROJECT_KEY` names are present without exposing values, but no issue key or mutation context has been selected; no Jira mutation is attempted in artifact mode
- Delegation: no subagents used; artifact gate executed inline
- Worktree policy: `avoid`
- Autonomous ledger: none; the user separately authorized local feature commits, rebases, and merges into `develop`; Jira, push, PR, reviewer, and remote merge mutations remain prohibited

## Resolved Roles

| Logical role | Resolution | Status |
|---|---|---|
| roadmap_generator | `krt-roadmap-cartographer` | resolved and used |
| brainstorm | `compound-engineering:ce-brainstorm` | resolved and used for RDM-001 and RDM-002 |
| plan | `compound-engineering:ce-plan` | resolved and used for RDM-001 and RDM-002 |
| document_review | `compound-engineering:ce-doc-review` | resolved and used for roadmap, planning input, and implementation plan |
| state_archivist | `krt-state-archivist` | available, not needed for compact initial state |
| work | `compound-engineering:ce-work` in return-to-caller/implementation-only mode | RU1, RU2, and RU3 complete |
| code review | `compound-engineering:ce-code-review` | RU1, RU2, and RU3 passed after local fixes |
| security review | `krt-security-sentinel` | RU1, RU2, and RU3 passed |
| release | `krt-release-marshal` adapted to the user-mandated local-only flow | RDM-001 fully merged locally |

## Context Readiness

- Product contract: sufficient and consolidated in `docs/initiative-brief.md`.
- Greenfield technical and delivery gaps are explicitly bounded as RDM-001 outcomes rather than silently assumed.
- Result: sufficient for a source-backed roadmap; no context blocker remains for roadmap review or the first item brainstorm.

## Artifact Status

| Artifact | Creation | Review gate |
|---|---|---|
| Readiness report | complete, superseded as active gate by the accepted brief | terminal historical artifact |
| Initiative brief | complete | accepted product authority from prior brainstorm |
| Roadmap | complete | passed (coherence, feasibility, product, security, scope, adversarial) |
| RDM-001 brainstorm | complete | planning input review passed (coherence, feasibility, product, security, scope, adversarial) |
| RDM-002 requirements | incorporated into its unified plan | accepted initiative decisions carried forward; no product blocker |
| RDM-001 implementation plan | `docs/plans/2026-07-22-001-feat-executable-privacy-proxy-foundation-plan.md` | implementation-ready; confidence check and document review passed |
| RDM-001 work package | `docs/work-packages/RDM-001-executable-privacy-proxy-foundation/2026-07-22-001-executable-foundation-work-package.md` | checker passed; package review and Reviewability Gate passed |
| RDM-002 implementation plan | `docs/plans/2026-07-22-002-feat-reversible-privacy-conversation-core-plan.md` | implementation-ready; coherence, feasibility, security, scope, and adversarial pass complete |
| RDM-002 work package | `docs/work-packages/RDM-002-reversible-privacy-conversation-core/2026-07-22-002-reversible-privacy-core-work-package.md` | bundled checker passed; three serial local review units |
| Later plans/packages | not created | dependency-ordered after RDM-002 gate |

## Blockers And Required Decisions

- No current blocker. The user explicitly selected `develop` as the integration branch and authorized local merges without PRs. Remote branch publication, PR creation, Jira mutation, reviewer notification, and remote merges are out of scope.
- Resolved product decision: default tool mode is provider-bound passthrough with local restoration of aliases already known from protected conversational text. It performs no discovery or transformation of other tool values. `docs/initiative-brief.md` was updated in the same transition.
- Resolved product decision: supported Codex and Claude Code versions form an explicitly tested range. Untested versions block by default and require a visibly unsupported, execution-scoped override. `docs/initiative-brief.md` was updated with R39 and AE9.
- No current product-contract blocker for RDM-001.
- RDM-001 scope must explicitly cover the supported-client version policy, non-inference egress inventory, proxy/child-process lifecycle, and isolated configuration/credential routing. These are additions to the foundation contract, not implementation decisions to silently defer.
- The user superseded the original `master` PR strategy with a local `develop` integration branch; RU1 carries all related planning artifacts on its semantic implementation branch.

## Assumptions And Safe Decisions

- Used Compound Master defaults because no arguments were supplied: `mode:artifacts`, `jira-policy:optional`, `production:unknown`, `parallel:false`, `delegation:auto`, `autonomy:guarded`, `worktree-policy:avoid`.
- Treats the initiative as greenfield; unresolved implementation choices are assigned to item-specific brainstorm/plan gates and cannot alter the accepted product behavior without escalation.
- Uses local `develop` as the integration base. `master` and `origin/master` remain unchanged and serve only as the seed commit for `develop`.
- Roadmap review ran inline and sequentially because the active repository instructions map subagent/persona work to the main thread. The optional cross-model additive pass did not run because no external route was sanctioned.
- A second brainstorm pressure test used current official Codex and Claude Code documentation. It confirmed configurable API base URLs and resumable sessions, while exposing client-version drift and default tool alias round-trip behavior as material contract surfaces.
- User authorized full autonomous continuation. Autonomy is `high` for local artifact, implementation, test, and review decisions; because no autonomous ledger exists, external mutation executor mode remains `manual-required` and no Jira/branch/push/PR/merge mutation is authorized through autonomy alone.
- RDM-001 plan confidence check strengthened ambient proxy/TLS handling, process-group cleanup, exact secure-keyring qualification, and separation of hermetic/system/compatibility gates.
- RDM-001 plan review ran inline and sequentially with coherence, feasibility, product, security, scope, and adversarial lenses; no actionable findings remain and client churn is retained as an advisory risk.
- RDM-001 package uses three review units: RU1 CLI/client contracts, RU2 proxy/supervisor runtime, RU3 keyring/compatibility evidence. Granularity favors reviewer outcomes over atomic plan units.
- Reviewability Gate: passed. Under the revised local-only delivery policy, each reviewed unit must be committed on its semantic feature branch, rebased onto `develop`, and merged locally before the next unit starts. No PR stack is created.
- Bundled `check_work_package.py` result: passed.
- Execution engine resolution: native inline. No `.compound-engineering/config.local.yaml`, typed engine carrier, or live external-route instruction applies; return-to-caller mode excludes starting a second goal engine.
- RU1 classification: dependent on the reviewed RDM-001 plan, high-risk because it establishes public CLI, subprocess, credential-environment, dependency, and compatibility contracts; execution remains serial.
- Created local branch `develop` from `origin/master` at `ba09b20` with no upstream, and retained `codex/client-compatibility-foundation` as the RU1 feature branch. No remote mutation has occurred.
- RU1 implementation result: U1 and U2 are complete. The repository now provides an installable Python 3.11+ package; `mr-hide` and `python -m mr_hide`; `codex`, `claude`, `doctor`, and `compatibility` commands; native-state-preserving adapters; tested-version enforcement; safe diagnostics; and a lock-driven SHA-pinned CI workflow.
- Impact Scan result: complete. The public CLI, adapter argv/environment, compatibility manifest, diagnostics, fixtures, and CI are new greenfield surfaces. No pre-existing code consumers exist; all discovered consumers are the RU1 code, tests, and documentation.
- Verification result: 45 tests passed against lock-resolved Python 3.11.15 and 3.13.7 environments; Ruff and strict mypy passed; sdist/wheel build and clean-wheel smoke passed; `uv lock --check` passed; local Codex 0.144.4 passed the candidate compatibility check. Claude Code is not installed locally, so its real-client matrix remains intentionally assigned to RU3.
- Code review result: six independently reproduced P1/P2 findings were fixed: upstream query leakage in CLI output, unlocked CI resolution, missing installed-wheel smoke, missing adapter conflict validation, argument parsing beyond native `--`, and unsafe decoding of invalid version output. Post-fix review found no P0-P2 issues. Cross-model review was unavailable because no different-family CLI was installed.
- Security review result: passed with no P0-P2 findings. Version probes use argv-only subprocesses, reject implicit current-directory resolution, receive a credential/state-sanitized environment, and never emit environment values. Upstream URLs reject userinfo/fragments and are not echoed. CI actions are SHA-pinned and the exported locked project dependency set reports no known vulnerabilities.
- CI break-prevention result: the workflow verifies the lock, tests Python 3.11/3.13 on Windows and Ubuntu, runs Ruff and mypy, audits exported locked dependencies, builds distributions, installs the wheel in a clean environment, and smokes both entry points plus packaged compatibility data.
- Recorded advisories: version-probe output has a timeout but no explicit byte cap; bootstrap `pip` belongs to the tooling environment rather than the project lock; real Claude/Linux compatibility evidence remains a RU3 responsibility. None weakens the RU1 gate.
- Superseded Release Marshal preflight: GitHub default remains `master` and `origin/develop` is absent, but the user explicitly replaced remote PR delivery with local merges into the new local `develop` branch.
- Jira release posture: optional and omitted. The strict checker returned `env-loaded-without-project-secret-file`: required variable names are present globally, but the checkout-local `.krt/env/jira-scribe.env` contract does not exist. No credentials were requested or used.
- Historical PR scope guardrail: the reconciled RU1 diff contained 2,930 additions and 46 deletions across 27 files before the deterministic local-env guard was added. The scope remains one coherent reviewed unit; no PR will be created.
- Historical PR body validation is retained only as audit evidence; it will not be published.
- RU1 local release result: four deterministic commits (`404c219`, `a628cbe`, `b7a0111`, `09eeb8b`) were rebased onto `develop` and merged locally with `--no-ff` as `06120c9`. The feature branch remains local; no push, PR, Jira, reviewer, or remote merge occurred.
- RU2 execution engine: native inline. The plan has two dependent units (U3 then U4), the active repository instructions map subagent work to sequential main-thread execution, `.compound-engineering/config.local.yaml` is absent, and no cross-model route applies.
- RU2 implementation result: U3 and U4 are complete. Declared Responses/Messages/counting routes forward raw request and response streams through a lifespan-scoped HTTPX client; the CLI now reserves an exclusive loopback endpoint, waits for Uvicorn readiness, launches one owned client process group, propagates exit status, and cleans up server, socket, child, and stubborn descendants across success, failure, and cancellation.
- RU2 Impact Scan result: complete. The changed public surfaces are the CLI launch behavior, three local HTTP routes, header/query/body/status streaming, adapter-provided child environments, process-group lifecycle, and synthetic upstream/client fixtures. All in-repository consumers are covered by unit/integration tests; persistent client configuration remains outside the mutation boundary.
- RU2 code review result: five P1/P2 findings were reproduced and fixed: Windows port reuse weakened endpoint exclusivity, HTTPX replayed upstream cookies, malformed upstream URLs escaped the safe CLI error contract, process cleanup errors skipped proxy/socket release, and cancellation could orphan the inner Uvicorn task. Focused regressions pass; the external cross-model pass was unavailable because no different-family CLI is installed.
- RU2 security result: passed with no remaining P0-P2 findings. The listener is IPv4 loopback-only and Windows-exclusive; upstream selection is explicit; URL userinfo/fragments and malformed targets are rejected; ambient proxies and upstream redirects are disabled; TLS verification remains enabled; hop-by-hop headers are stripped; bodies and credentials are not logged; child execution is shell-free; and force cleanup targets only the owned group/tree.
- RU2 verification result: 77 hermetic tests passed on lock-resolved Python 3.11 and 3.13; Ruff and strict mypy passed; sdist/wheel build and clean-wheel smoke passed. The focused post-review slice passed 25 tests. The Windows exclusive-bind regression ran locally; Linux lifecycle coverage remains represented by the required CI matrix and is not claimed as locally executed.
- RU2 residual risk: on Windows, confirming every descendant after a cooperative parent exits before a signal-resistant descendant ultimately requires stronger OS ownership such as Job Objects; the current stubborn parent/descendant tree and unrelated-process isolation paths pass. This is advisory for the current supported foundation and remains visible for RU3 cross-platform evidence.
- RU2 local release result: five reviewed commits were rebased onto `develop` and merged locally with `--no-ff` as `bb9f079`. No remote mutation occurred.
- RU3 implementation result: U5 and U6 are complete. Exact approved Windows Credential Locker and Linux Secret Service backend types are qualified with a random set/get/delete probe; the CLI reports only redacted capability state. Pinned real-client contracts exercise Codex Responses and Claude Messages launch/resume against a protocol-shaped local upstream, while generated evidence distinguishes mediated inference from non-inference egress and the still-absent privacy transformation.
- RU3 local compatibility evidence: Codex `0.144.4` and `0.145.0`, and Claude Code `2.1.216` and `2.1.217`, passed on Windows with exact-version assertions, dummy credentials, isolated client state, and no live provider. Linux cells are configured but not claimed as locally executed because this local-only run cannot execute GitHub-hosted Ubuntu jobs; the exact command is encoded in `.github/workflows/compatibility.yml`.
- RU3 verification result: 87 hermetic core tests passed on lock-resolved Python 3.11 and 3.13; four real-client Windows cells passed; the actual Windows Credential Locker probe passed; focused keyring/evidence coverage passed 13 tests; Ruff, strict mypy, YAML parsing, generated-doc drift, build, and wheel-content checks passed.
- RU3 review finding: backend discovery exceptions could escape the redacted `doctor` contract. The failure is now caught and reported as `unavailable; probe-failed`, with a regression test. No credential value or exception detail is emitted.
- RU3 code/security review result: passed with no remaining P0-P2 findings. The external cross-model additive pass was unavailable without invoking a live provider and was not required for the local gate.
- RU3 local release result: three reviewed commits (`cca91f4`, `3d11d4c`, `5bdf422`) were rebased onto `develop` and merged locally with `--no-ff` as `8494c90`. No push, PR, Jira mutation, reviewer notification, or remote merge occurred.
- RDM-002 artifact result: the plan preserves the accepted R9-R34 behavior while separating provider-neutral detection/transformation, encrypted state, and policy lifecycle into three review units. Official Presidio, cryptography, and tiktoken documentation grounded current dependency/API assumptions.
- RDM-002 plan review result: passed inline because repository instructions require sequential main-thread execution. The review replaced an unprovable generic rollback claim with stale-writer protection, added bounded custom-regex execution, canonical conversation identifiers, and explicit handling for raw text colliding with an existing substitute.
- RDM-002 package checker: passed with RU1 selected for execution and local-only PR metadata retained solely for checker/audit compatibility.
- RDM-002 RU1 implementation result: provider-neutral immutable mapping models, deterministic overlap/normalization, collision-safe compact aliases, compatibility surrogates, explicit cost metrics, longest-match restoration, Presidio English/Spanish integration, timeout-bounded technical-secret recognizers, declarative custom recognizers, and a safe default composite detector are complete.
- RDM-002 RU1 verification result: 141 hermetic tests passed on lock-resolved Python 3.11 and 3.13; 57 focused privacy/model tests passed locally, including three real Presidio tests with `en_core_web_sm==3.8.0` and `es_core_news_sm==3.8.0`; Ruff, strict mypy, lock validation, build, clean-wheel install/import smoke, dependency audit, and offline suffix-list evidence passed. The locked dependency graph reports no known vulnerabilities.
- RDM-002 RU1 review result: confirmed issues were fixed for empty-detector fail-open, multiple-candidate collision escape, ambiguous/unknown/corrupt mapping restoration, recursive allocation denial of service, eager spaCy loading, unlabelled byte-vs-token costs, exception-cause leakage, implicit tiktoken resolution, and tldextract network updates. No P0-P2 findings remain.
- RDM-002 RU1 local release result: five reviewed commits (`84c2033`, `58b2f14`, `79c0bf0`, `0ac85af`, `231dbb8`) were rebased onto `develop` and merged locally with `--no-ff` as `04a283f`. No remote mutation occurred.
- RDM-002 RU2 implementation result: authenticated AES-256-GCM conversation envelopes use fresh 96-bit nonces, schema-and-identity AAD, HKDF-SHA256 per-conversation keys, and a 256-bit installation master key held only by an exact approved OS keyring backend. Canonical UUIDs, strict schemas, duplicate-key rejection, safe reason codes, atomic same-directory replacement, file locking, revision checks, and stale-writer rejection are complete.
- RDM-002 RU2 verification result: 185 hermetic tests passed on Python 3.11.15 and 3.13.7; the focused state suite passed 42 tests with one Windows-inapplicable POSIX permission assertion skipped. Ruff, strict mypy, sdist/wheel build, clean-wheel CLI/resource/state import smoke, and the actual Windows Credential Locker probe passed.
- RDM-002 RU2 dependency audit result: no known vulnerability was found in the installed project dependency set. Six ignored findings belonged only to bootstrap `pip 25.2`, which is neither declared in `pyproject.toml` nor included in the project wheel/lock export; CI audits the exported locked dependency set without bootstrap pip.
- RDM-002 RU2 review result: confirmed seams were fixed for non-integer revisions, invalid runtime state types, nonce-factory type/exception leakage, master-key RNG exception leakage, package discovery for shared test fixtures, and missing wheel coverage for the public state API. No P0-P2 finding remains.
- RDM-002 RU2 security result: tamper, wrong key, wrong identity, malformed/duplicate envelopes, invalid stored key, unapproved keyring subclasses, concurrent key bootstrap, stale/concurrent writers, interrupted atomic replacement, copied ciphertext plaintext leakage, and error sentinel leakage are covered. Loading never creates a replacement key. The master key and plaintext originals do not appear in the vault payload.
- RDM-002 RU2 local release result: four reviewed commits (`48357ed`, `daf36af`, `8c8a612`, `5c8ce85`) were rebased onto `develop` and merged locally with `--no-ff` as `cdd5c7c`. No remote mutation occurred.
- RDM-002 RU3 implementation result: protocol-neutral default, safe-tool-calls, and tool-compatibility decisions cover every direction/content-kind pair. Conversation lifecycle now exposes protected, bypassed, blocked, missing, and expired results; refreshes activity only after successful persisted operations; requires explicit bypass warning acceptance; preserves bypass isolation/visibility; and performs idempotent 30-day cleanup with locked revalidation.
- RDM-002 RU3 evidence result: `doctor` reports redacted English/Spanish model availability; CI adds exact model wheels on Windows and Linux plus a deterministic synthetic alias benchmark; system-keyring coverage now verifies actual separated master-key storage; operator documentation states detection limits, default-tool exposure, policy behavior, key separation, and retention.
- RDM-002 RU3 verification result: 236 tests passed locally on Python 3.13 including exact English/Spanish Presidio models and the approved Windows Credential Locker; 231 hermetic tests passed on Python 3.11. Ruff, strict mypy over 41 source files, workflow YAML parsing, deterministic benchmark, sdist/wheel build, and clean-wheel imports for policy/lifecycle/vault/PEP-561 APIs passed.
- RDM-002 RU3 review result: confirmed issues were fixed for untyped policy inputs, naive retention cutoffs, deletion after a candidate was concurrently refreshed, fail-open passthrough when activity persistence fails, model diagnostic leakage/load behavior, isolated system-keyring test identity, and wheel omission of new public APIs. No P0-P2 finding remains.
- RDM-002 RU3 security result: blocked results cannot carry text; processing, restoration, revision, clock, keyring, and persistence failures never return raw or partial values. Default tool passthrough is a deliberate warned policy action, not fallback. Expired ciphertext is deleted at the exact 30-day boundary and never silently recreated under the old identity.

## Exact Next Invocation

```text
Commit the reviewed RU3 implementation/evidence, rebase `codex/privacy-policy-lifecycle` onto local `develop`, and merge locally with `--no-ff`. Then create and review the RDM-003 artifact packet. Do not push or create a PR.
```
