# Traffic boundary

Mr Hide RDM-001 mediates only the declared inference routes below:

- `/v1/messages`
- `/v1/messages/count_tokens`
- `/v1/responses`

The listener binds only to loopback. Requests preserve bodies, raw query bytes,
status,
stream order, and end-to-end headers after hop-by-hop filtering.

## Outside the boundary

Authentication, client login, model discovery outside declared routes,
telemetry, crash
reporting, update checks, plugin discovery, and provider-bound tool traffic are not
intercepted merely because the inference base URL points at Mr Hide. Their exact
behavior can change with client versions and is recorded as documented, observed,
or unknown rather
than claimed as protected.

## Privacy status

RDM-001 performs no Presidio detection, alias substitution, restoration,
encrypted mapping
storage, or privacy-complete transformation. Those capabilities begin in RDM-002.
