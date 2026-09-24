# Traffic boundary

Mr Hide mediates only the declared inference routes below:

- `/v1/messages`
- `/v1/messages/count_tokens`
- `/v1/responses`

The listener binds only to loopback. Protected routes rewrite eligible JSON fields;
raw forwarding preserves bodies. Requests preserve raw query bytes,
status,
stream order, and end-to-end headers after hop-by-hop filtering. OpenAI
Responses and Anthropic Messages request/response JSON and SSE use explicit
bounded field matrices. Token-count requests use the same protected Messages
representation without mutating state from structural count responses.

## Outside the boundary

Authentication, client login, model discovery outside declared routes,
telemetry, crash
reporting, update checks, plugin discovery, and provider-bound tool traffic are not
intercepted merely because the inference base URL points at Mr Hide. Their exact
behavior can change with client versions and is recorded as documented, observed,
or unknown rather
than claimed as protected.

## Privacy status

Supported Codex `/v1/responses` and Claude `/v1/messages` traffic use local
detection, reversible substitution/restoration, encrypted conversation mappings,
native resume bindings, retention, bypass, and the selected tool policy.
`/v1/messages/count_tokens` shares the protected request snapshot. Unknown
protocol content is preserved without recursive inspection.
