# Traffic boundary

Mr Hide mediates only the declared inference routes below:

- `/v1/messages`
- `/v1/messages/count_tokens`
- `/v1/responses`

The listener binds only to loopback. Requests preserve bodies, raw query bytes,
status,
stream order, and end-to-end headers after hop-by-hop filtering. OpenAI
Responses request/response JSON and SSE use an explicit bounded field matrix;
Anthropic routes remain byte-preserving until RDM-004.

## Outside the boundary

Authentication, client login, model discovery outside declared routes,
telemetry, crash
reporting, update checks, plugin discovery, and provider-bound tool traffic are not
intercepted merely because the inference base URL points at Mr Hide. Their exact
behavior can change with client versions and is recorded as documented, observed,
or unknown rather
than claimed as protected.

## Privacy status

Supported Codex `/v1/responses` traffic uses local detection, reversible
substitution/restoration, encrypted conversation mappings, native resume
bindings, retention, bypass, and the selected tool policy. Unknown protocol
content is preserved without recursive inspection. `/v1/messages` and
`/v1/messages/count_tokens` remain raw until their dedicated integration.
