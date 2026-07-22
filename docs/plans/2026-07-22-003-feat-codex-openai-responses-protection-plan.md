---
roadmap_item: RDM-003
status: implementation-ready
date: 2026-07-22
integration_base: develop
delivery: local-only
---

# Protect Codex over OpenAI Responses

## Objective

Apply the reviewed RDM-002 privacy core to the OpenAI Responses traffic used by supported Codex versions while preserving route, unknown fields, HTTP errors, SSE order, usage/counting data, native client state, and the three tool policies. This is protocol mediation, not OpenAI-to-Anthropic translation or model routing.

## Accepted behavior

- Every launch receives a new canonical Mr Hide conversation UUID unless a validated native Codex resume identity is bound to an existing unexpired vault.
- Provider-bound conversational text is detected and transformed before forwarding. Known failures return a local safe error before any upstream request.
- Default provider-bound tool definitions, arguments, outputs, and history remain byte-semantically unchanged after JSON reserialization and carry the existing `tool-data-unprotected` warning state. Safe mode aliases them; compatibility mode uses surrogates.
- Provider-to-local output text and tool arguments restore only established mappings. Unknown aliases, invalid JSON, invalid SSE, state failures, or persistence failures block; none falls back to the raw event/body.
- Unknown JSON members and unknown SSE event types are preserved without recursive string rewriting. Only an explicit field matrix is eligible. The declared `tools` subtree is a deliberate exception: all of its JSON keys and string values are tool-definition content under safe/compatibility policy.
- Counting/usage fields remain structural metadata. Any client-observed counting route is added only with pinned Codex evidence; RDM-003 does not invent an undocumented OpenAI endpoint.

## Requirements

- R3.1. Define a typed Responses field matrix covering `instructions`, string `input`, message `content` strings, `input_text.text`, output `output_text.text`, response/error messages, function/custom/MCP tool definitions and argument/output strings, and the corresponding streamed deltas/done events used by Codex.
- R3.2. Preserve non-text modalities, IDs, roles, annotations, reasoning encrypted content, usage, errors, status, sequence numbers, unknown members, and unknown event types.
- R3.3. Parse JSON with duplicate-key rejection, bounded body/event sizes, UTF-8 enforcement, and safe reason codes. Reject trailing data and non-object request roots.
- R3.4. Parse SSE incrementally across arbitrary transport chunk boundaries, preserve comments/fields/order for untouched events, and never emit a partially restored sensitive value. Once an eligible event is buffered, later frames queue behind it until the eligible logical value completes or the bounded stream fails, so no event can overtake withheld data.
- R3.5. Buffer eligible streamed text/tool deltas until their protocol completion boundary, transform or restore atomically, then emit valid ordered Responses events. Function and MCP argument strings are decoded as strict duplicate-safe inner JSON and transformed recursively across keys/string leaves before being reserialized; custom-tool freeform input remains text. Do not claim token-for-token or chunk-for-chunk equivalence for eligible text.
- R3.6. Compose one conversation service per bound conversation with injected detector, policy, vault repository, and clock; never instantiate a fallback detector or key store after a capability error.
- R3.6a. Stage every multi-field request transformation against one in-memory mapping snapshot and persist exactly one next revision only after the entire body succeeds. A later-field failure leaves mappings and activity unchanged. Stream restoration similarly refreshes activity only after the complete bounded stream transforms successfully.
- R3.7. Bind Codex launch/resume to an isolated local conversation registry keyed by the exact client-native resume identity. Reject ambiguous, missing, malformed, expired, or cross-client bindings.
- R3.8. Add CLI policy selection and visible conversation/policy/bypass warnings without printing resume IDs, mappings, request text, or upstream details.
- R3.9. Preserve existing transparent forwarding for Anthropic routes until RDM-004 and retain raw forwarding for undeclared content outside the Responses matrix.
- R3.10. Prove current pinned Codex contracts for new launch, resume, ordinary JSON, SSE output, tool calls/results, unknown fields/events, upstream errors, and all policy modes without live provider credentials.

## Technical design

### Protocol boundary

- `src/mr_hide/protocols/responses/fields.py`: explicit JSON path/type classifier returning `ContentKind`, direction, and eligibility.
- `src/mr_hide/protocols/responses/json_body.py`: strict bounded outer/inner JSON decode/encode and copy-on-write traversal. Unknown subtrees are retained exactly as values, never inspected for PII; recursive traversal is allowed only inside declared tool definitions and strict function/MCP argument documents.
- `src/mr_hide/protocols/responses/sse.py`: incremental SSE framing and Responses event transformation. Raw frames are retained for unknown/untouched events; eligible deltas are accumulated by item/output/content index and emitted only after successful restoration.
- `src/mr_hide/protocols/responses/handler.py`: request/response composition with `ConversationService`, detector, and policy; produces safe HTTP errors before forwarding when possible.
- `src/mr_hide/state/bindings.py`: encrypted or non-secret local binding from client kind plus hashed native resume identity to canonical conversation UUID. The native identity is never used as a path or logged.

### Runtime composition

`create_proxy_app` receives an explicit Responses runtime dependency. `forward_request` delegates `/v1/responses` only when configured; the two Anthropic routes keep the reviewed raw path. Transformed requests use bounded buffered JSON. Non-streaming responses are buffered to the configured limit; SSE responses use a bounded ordered queue that may delay eligible content but never reorders frames, and close upstream on every exit.

The CLI chooses `default`, `safe-tool-calls`, or `tool-compatibility`, creates/resumes a conversation before starting the child, and passes the prepared runtime into the supervisor. A launch failure after state creation leaves an inert expiring vault; it never silently reuses another conversation.

## Implementation units

### U1. Strict Responses JSON and SSE transformers

- Add bounded duplicate-safe JSON parsing, the explicit request/response/tool field matrix, copy-on-write transforms, SSE framing, eligible event aggregation, and unknown preservation.
- Tests: string/array inputs, message parts, instructions, tools, function outputs, all three policies, unknown nested strings, duplicate/truncated/oversized JSON, chunk-split SSE, CRLF, comments, unknown events, tool-argument deltas, output-text deltas, errors, and no partial emission.

### U2. Codex conversation binding and runtime integration

- Add conversation registry, launch/resume creation, CLI policy options/status, Responses handler composition, safe local HTTP errors, and pinned Codex end-to-end fixtures.
- Tests: new/resume/expired binding, isolation, concurrent launch, upstream not called on failure, HTTP/SSE headers/status, usage/counting preservation, tool round trips, client exit/cleanup, and real pinned Codex contracts.

### U3. Evidence and documentation closure

- Update CI, clean-wheel imports, protocol/traffic documentation, compatibility evidence, and sentinel/leak tests.
- Tests: Python 3.11/3.13, Windows/Linux-compatible core, pinned Codex Windows/Linux matrix, Ruff, strict mypy, audit, build, wheel smoke, and artifact scan.

## Review and security gates

- Correctness: no eligible text bypasses the matrix; no unknown field is recursively transformed; SSE aggregation produces valid order and completion semantics.
- Reliability: cancellation closes both request and response streams; bounded buffers reject rather than exhaust memory; upstream errors remain protocol-visible when no privacy transformation is required.
- Security: duplicate keys, parser differentials, JSON-in-string tool arguments, alias split across SSE chunks, malicious event indices, native resume path traversal, cross-conversation restoration, and persistence failure are adversarial regression targets.
- Review threshold: fix every confirmed P0-P2 before local integration.

## Sources

- OpenAI Responses input/output and tool object reference: https://platform.openai.com/docs/api-reference/responses
- OpenAI Responses streaming event reference: https://platform.openai.com/docs/api-reference/responses-streaming
- OpenAI developer quickstart for structured input and SSE: https://platform.openai.com/docs/quickstart
- Local pinned Codex contract evidence: `docs/compatibility.md` and `tests/compatibility/test_codex_contract.py`.

## Verification contract

The capability is complete only when captured upstream traffic contains no original eligible sentinel outside an explicitly bypassed conversation or default provider-bound tool field; every restored local output matches its conversation mapping; unknown fields/events survive; no blocked operation reaches upstream; and supported Codex launch/resume fixtures pass without live provider access.
