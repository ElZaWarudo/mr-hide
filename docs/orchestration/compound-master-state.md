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

- Phase: RDM-004 RU1 local release gate
- Result: RDM-001 through RDM-003 are locally integrated. RDM-004 RU1 strict Anthropic Messages/count JSON and SSE transformers are implemented, reviewed, and verified; the remaining action is the authorized local rebase and merge before RU2.
- Primary artifact: `docs/plans/2026-07-22-004-feat-claude-anthropic-messages-protection-plan.md`
- Artifact classification: `implementation-ready unified code plan`

## Preflight

- Workspace: `C:/Users/Mayor/Documents/Caribbean/mr-hide`
- Git repository: yes; remote `origin` is configured
- Integration base: local `develop` at `af00f04`, created from the matching `origin/master` seed and advanced only through reviewed local feature merges; it has no upstream
- Active artifact/implementation branch: `codex/anthropic-messages-protection`, created from local `develop` after the RDM-003 closeout
- Working tree at the RU1 release gate: reviewed RDM-004 Messages transformer source, tests, wheel smoke, work-package evidence, and orchestration state only
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
| RDM-003 implementation plan | `docs/plans/2026-07-22-003-feat-codex-openai-responses-protection-plan.md` | implementation-ready; inline document review passed |
| RDM-003 work package | `docs/work-packages/RDM-003-codex-openai-responses/2026-07-22-003-codex-responses-work-package.md` | bundled checker passed; RU1 selected before RU2 runtime integration |
| RDM-004 implementation plan | `docs/plans/2026-07-22-004-feat-claude-anthropic-messages-protection-plan.md` | implementation-ready; inline review passed |
| RDM-004 work package | `docs/work-packages/RDM-004-claude-anthropic-messages/2026-07-22-004-claude-messages-work-package.md` | two serial local review units; RU1 selected |
| Later plans/packages | not created | dependency-ordered after RDM-004 gate |

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
- RDM-002 RU3 local release result: four reviewed commits (`0527ac0`, `e69201b`, `4222747`, `bb1ee7d`) were rebased onto `develop` and merged locally with `--no-ff` as `89b9487`. RDM-002 is complete; no remote mutation occurred.
- RDM-003 artifact result: current official OpenAI Responses input/tool and streaming-event references plus pinned local Codex evidence define an explicit field/event matrix. Unknown structures remain opaque, while declared tool definitions and strict inner function/MCP argument JSON receive policy-aware traversal.
- RDM-003 plan review result: passed inline under the repository's sequential-agent rule. The review added strict inner-JSON handling to avoid invalid escaped arguments, ordered SSE withholding so later events cannot overtake buffered sensitive deltas, explicit error-message restoration, bounded parsing, and a no-invented-counting-route rule.
- RDM-003 package result: two serial units isolate pure bounded JSON/SSE transformers from native session binding and proxy/CLI integration. The bundled checker passed; its generated-artifact warning is addressed by keeping mechanically checked compatibility evidence beside the RU2 runtime it attests.
- RDM-003 RU1 implementation result: explicit request/response JSON and SSE event matrices transform only declared conversational and tool surfaces. Outer and inner JSON reject duplicates and non-finite values, parsing and transformed output are bounded, unknown protocol subtrees/events remain opaque, and callback failures expose stable reason codes rather than source data.
- RDM-003 RU1 streaming result: arbitrary transport chunking, LF/CRLF frames, delta/done aggregation, strict function/MCP argument JSON, output/content/reasoning/error events, and ordered withholding are covered. A malformed, incomplete, mismatched, or oversized eligible stream emits no partial transformed output.
- RDM-003 RU1 review result: the implementation includes transactional whole-body requirements for RU2 composition, strict known-event typing, complete added/done event handling, post-transform expansion limits, and leakage regressions. The only sentinel scan match is an intentional exception payload whose test proves it is absent from the public error. No P0-P2 finding remains.
- RDM-003 RU1 verification result: 36 focused protocol tests passed; the full Python 3.13 suite passed 272 tests with one POSIX-only skip and four compatibility deselections; the Python 3.11 suite passed 267 tests with one skip and nine deselections. Ruff, strict mypy over 45 source files, `git diff --check`, sdist/wheel build, and clean-wheel import smoke passed.
- RDM-003 RU1 local release result: four reviewed commits (`64ff225`, `1104f02`, `dcc3959`, `7c4939d`) were rebased onto `develop` and merged locally with `--no-ff` as `9f9e7c0`. No push, PR, Jira mutation, reviewer notification, or remote merge occurred.
- RDM-003 RU2 implementation result: Codex requests require a canonical native prompt-cache/session UUID, store only a client-scoped SHA-256 binding key, and reuse exactly one encrypted vault on explicit resume. New launches receive fresh conversation UUIDs. Request JSON is transformed and committed before upstream; response JSON/SSE is bounded, restored, and committed only after complete success. Anthropic routes retain raw forwarding.
- RDM-003 RU2 policy/CLI result: `default`, `safe-tool-calls`, and `tool-compatibility` are execution-visible; default warns `tool-data-unprotected`; bypass requires explicit warning acceptance and remains visible after resume. A resumed vault rejects substitution-mode changes before activity refresh.
- RDM-003 RU2 review result: confirmed P1/P2 issues were fixed for incomplete Codex SSE fixture sequencing, resume options before the UUID, ambiguous `resume --last`, hidden persisted bypass state, policy-mode changes after resume, compatibility-test state/keyring contamination, and missing Linux Secret Service setup. No P0-P2 finding remains.
- RDM-003 RU2 verification result: the full Python 3.13 suite passed 291 tests with one POSIX-only skip and four compatibility deselections; the hermetic Python 3.11 suite passed 286 tests with one skip and nine deselections; a 76-test focused gate passed. Ruff, strict mypy over 47 source files, workflow YAML parsing, generated-evidence drift, `git diff --check`, sdist/wheel build, and clean-wheel imports passed.
- RDM-003 RU2 compatibility result: pinned native Codex `0.144.4` passed protected Windows launch plus explicit native resume against protocol-shaped local Responses SSE, isolated client/state directories, a test-scoped OS-keyring service, and a dummy credential. Codex `0.145.0` plus Windows/Linux cells remain encoded in the exact-version compatibility workflow and are not newly claimed as locally rerun after privacy integration.
- RDM-003 RU2 dependency audit result: the project dependency declarations and lock are unchanged from the clean exported-lock audit. A local environment audit reported only six advisories against bootstrap `pip 25.2`; pip is not declared by the project or shipped in its wheel. The two pinned spaCy model wheels are outside PyPI audit resolution.
- RDM-003 RU2 local release result: four reviewed commits (`de898f6`, `a07823e`, `1b6cc0b`, `b922eae`) were rebased onto `develop` and merged locally with `--no-ff` as `af00f04`. RDM-003 is complete; no push, PR, Jira mutation, reviewer notification, or remote merge occurred.
- RDM-004 artifact result: official Anthropic Messages, streaming, token-counting, and Claude Code CLI references ground the explicit JSON/SSE matrix and the documented canonical `--session-id` launch mechanism. New sessions can be bound before process start; ambiguous picker/name/continue forms remain unsupported and fail closed.
- RDM-004 plan review result: passed inline under the repository's sequential-agent rule. The design keeps protocol field knowledge out of the provider-neutral transaction, applies the same protected representation to count requests, withholds partial tool JSON until `content_block_stop`, and rejects session conflicts before child launch.
- RDM-004 package result: two serial units isolate pure bounded Messages/count/SSE parsers from shared-transaction extraction, Claude binding, proxy/CLI composition, and compatibility evidence.
- RDM-004 RU1 implementation result: strict duplicate-safe and non-finite-safe JSON transforms cover declared Anthropic system, message text, tool use/result, document, search-result, tool-definition, response text/tool, and error surfaces while preserving binary, thinking, metadata, and unknown structures as opaque data. Token-count requests reuse the same request transform without introducing provider state.
- RDM-004 RU1 streaming result: bounded whole-stream withholding supports LF/CRLF framing, arbitrary transport chunks, declared event/type matching, indexed content-block lifecycles, text-delta aggregation, and strict partial tool-input JSON aggregation. Unknown events remain byte-exact, and malformed, incomplete, oversized, mismatched, or out-of-order eligible streams emit no transformed prefix.
- RDM-004 RU1 review result: an adversarial pass found that accumulated `input_json_delta.partial_json` needed its own pre-transform byte, Unicode, and depth constraints. The implementation and a deep-partial regression now enforce those bounds before recursive tool transformation. No P0-P2 finding remains.
- RDM-004 RU1 verification result: 23 focused Messages tests and 66 combined Messages/Responses protocol tests passed. The full Python 3.13 suite passed 314 tests with one POSIX-only skip and four compatibility deselections; Python 3.11 passed 309 tests with one skip and nine deselections. Ruff, strict mypy over 50 source files, `git diff --check`, sdist/wheel build, and clean-wheel protocol import smoke passed.

## Exact Next Invocation

```text
Commit the reviewed RDM-004 RU1 implementation, rebase `codex/anthropic-messages-protection` onto local `develop`, merge it locally with `--no-ff`, then create `codex/claude-messages-runtime` for RU2. Do not push or create a PR.
```
