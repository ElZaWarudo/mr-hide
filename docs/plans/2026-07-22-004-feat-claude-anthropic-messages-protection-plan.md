---
roadmap_item: RDM-004
status: implementation-ready
date: 2026-07-22
integration_base: develop
delivery: local-only
---

# Protect Claude Code over Anthropic Messages

## Objective

Apply the reviewed privacy transaction and encrypted conversation lifecycle to the exact Anthropic Messages and token-counting traffic used by supported Claude Code versions. Preserve native Claude Code state and protocol semantics without translating to OpenAI, routing models, or recursively rewriting unknown content.

## Accepted behavior

- New Claude Code launches receive a launcher-owned canonical native session UUID through the documented `--session-id` flag and a fresh Mr Hide conversation UUID; the binding is persisted before the child starts. Explicit `--resume`/`-r` UUIDs reuse only their bound, active vault.
- Ambiguous picker/name/`--continue` forms block because they do not provide a canonical identity. User-supplied `--session-id` conflicts with the launcher-owned binding and is rejected.
- `/v1/messages` and `/v1/messages/count_tokens` share the same strict request field matrix. Count responses remain structural JSON and never mutate mappings.
- Conversational text in `system`, message strings, `text` blocks, and eligible document/search text is protected. Binary/image/PDF data, cache controls, citations, IDs, roles, usage, thinking signatures, and unknown blocks remain opaque.
- Client-tool definitions, `tool_use.input`, and `tool_result.content` follow the selected tool policy. Default tool data passes unchanged with the existing warning; safe mode aliases; compatibility mode uses surrogates.
- Provider output text and tool-use input restore only known mappings. Invalid JSON/SSE, duplicate keys, malformed indices, unknown aliases, state errors, or incomplete deltas block without raw fallback.

## Requirements

- R4.1. Define an explicit typed Messages matrix for top-level `system`, `messages[].content`, supported text/document/search blocks, `tools`, `tool_use`, and `tool_result`; preserve unknown fields and block types without recursive inspection.
- R4.2. Strictly decode bounded UTF-8 JSON with duplicate-key and non-finite-value rejection. Transform a copy and enforce post-transform size/depth limits.
- R4.3. Protect both `/v1/messages` and `/v1/messages/count_tokens` requests using one transactional mapping snapshot. Persist exactly once only after the complete body succeeds; count responses do not refresh or change state.
- R4.4. Parse Anthropic SSE across arbitrary transport chunks. Preserve comments, event names, order, message/usage metadata, ping events, and unknown event types. Buffer eligible `text_delta` and `input_json_delta.partial_json` until their `content_block_stop` boundary.
- R4.5. Reconstruct tool input from strict duplicate-safe partial JSON, restore recursively across JSON keys/string leaves, and emit a valid ordered content-block event sequence. No later frame may overtake withheld eligible content.
- R4.6. Extract the provider error message only from declared error envelopes; restore known aliases and keep safe HTTP/status behavior. Never expose upstream body, native identity, mapping, or exception text in local errors/logs.
- R4.7. Refactor the RDM-003 mapping transaction into one provider-neutral runtime component used by both protocols. Protocol modules retain their own field matrices and native-identity rules.
- R4.8. For new Claude launches, generate and validate a canonical UUID, bind it before state creation completes, and append documented `--session-id`. Explicit canonical `--resume`/`-r` looks up the binding; `--continue`, missing resume values, names, and conflicts block.
- R4.9. Expose the same tool-policy and bypass CLI options/status for Claude as Codex. A resumed bypass remains visible; a substitution-mode change blocks before activity refresh.
- R4.10. Prove pinned Claude Code launch/resume, ordinary JSON, token counting, SSE text, tool use/result, errors, unknown fields/events, all policies, and cleanup without live provider credentials.

## Technical design

- `src/mr_hide/protocols/messages/json_body.py`: bounded copy-on-write request/response/count traversal and strict recursive tool JSON handling.
- `src/mr_hide/protocols/messages/sse.py`: bounded Anthropic framing and content-block aggregation keyed by validated indices.
- `src/mr_hide/protocols/messages/handler.py`: Messages/count routing, safe HTTP failures, response restoration, and no-state-mutation count responses.
- `src/mr_hide/runtime/privacy.py`: provider-neutral staged transaction and launch preparation extracted from the Responses handler without provider field knowledge.
- `src/mr_hide/clients/claude.py`: canonical explicit resume validation and launcher-owned `--session-id` conflict protection.

## Implementation units

### U1. Strict Messages JSON/SSE transformers

- Implement the explicit request/response/count field matrix, bounded JSON, tool definition/input/result rules, SSE framing, text/tool delta aggregation, unknown preservation, and fail-before-output behavior.
- Tests cover string/array messages, system blocks, tools, results, documents/search text, count requests, all policies, duplicate/truncated/oversized JSON, arbitrary SSE chunks, malformed indices, partial tool JSON, errors, and unknown events.

### U2. Claude conversation binding and runtime integration

- Extract the shared transaction, add Messages/count handlers, create/resume binding, CLI policy/bypass parity, exact session injection, compatibility fixtures, documentation, wheel, and CI closure.
- Tests cover new/resume/expired/isolation/concurrency, session conflicts, count behavior, upstream-not-called failures, headers/status, real pinned Claude versions, and leakage sentinels.

## Review and security gates

- Correctness: request and count matrices match; streaming emits valid block order; tool partial JSON reconstructs exactly; unknown protocol data remains untouched.
- Reliability: request/response streams close on every path; bounded buffers fail closed; stale writers and concurrent resumes never cross mappings.
- Security: duplicate JSON keys, nested tool objects, split aliases/JSON escapes, negative/huge indices, resume path traversal/names, `--continue`, user-owned session IDs, source-bearing errors, and cross-client binding attempts are adversarial targets.
- Review threshold: fix every confirmed P0-P2 before each local merge.

## Sources

- Anthropic Messages request/content reference: https://platform.claude.com/docs/en/api/messages/create
- Anthropic streaming event reference: https://platform.claude.com/docs/en/build-with-claude/streaming
- Anthropic token counting reference: https://platform.claude.com/docs/en/api/typescript/messages/count_tokens
- Claude Code CLI session flags: https://code.claude.com/docs/en/cli-usage
- Local pinned-client evidence: `docs/compatibility.md` and `tests/compatibility/test_claude_contract.py`.

## Verification contract

The capability is complete only when protected captured Messages/count traffic excludes every eligible original sentinel outside default tool data or an explicitly bypassed conversation; restored output matches only its bound vault; count requests use the same protected representation; unknown fields/events survive; blocked operations never reach upstream; and supported Claude Code launch/resume fixtures pass without live credentials.
