# Client compatibility

This page is generated from `src/mr_hide/compatibility.toml`.
Candidate ranges are not release support until every required Windows/Linux cell passes.

## Candidate ranges

| Client | Range | Evidence status | Note |
|---|---|---|---|
| Codex | `>=0.144.4,<0.146.0` | candidate | Candidate range; real-client Windows/Linux evidence is required before release support is advertised. |
| Claude Code | `>=2.1.216,<=2.1.217` | candidate | Candidate range; real-client Windows/Linux evidence is required before release support is advertised. |

## Required matrix

| Client | Versions | Platforms | Flow | Routes | Status |
|---|---|---|---|---|---|
| codex | 0.144.4, 0.145.0 | windows, linux | non-interactive Responses round trip | `/v1/responses` | required |
| claude | 2.1.216, 2.1.217 | windows, linux | non-interactive Messages launch and native resume | `/v1/messages`, `/v1/messages/count_tokens` | required |

## Recorded local evidence

| Date | Client | Version | Platform | Flow | Result | Limitations |
|---|---|---|---|---|---|---|
| 2026-07-22 | codex | 0.144.4 | windows | non-interactive Responses round trip | pass | Local candidate evidence only; the complete Windows/Linux boundary matrix remains required. |
| 2026-07-22 | claude | 2.1.216 | windows | non-interactive Messages launch and native resume | pass | Local candidate evidence only; the complete Windows/Linux boundary matrix remains required. |
| 2026-07-22 | codex | 0.145.0 | windows | non-interactive Responses round trip | pass | Local candidate evidence only; the complete Windows/Linux boundary matrix remains required. |
| 2026-07-22 | claude | 2.1.217 | windows | non-interactive Messages launch and native resume | pass | Local candidate evidence only; the complete Windows/Linux boundary matrix remains required. |

Compatibility runs use protocol-shaped local responses and dummy credentials.
Overrides
for versions outside these ranges never update this evidence or expand support.
