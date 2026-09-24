# Client compatibility

This page is generated from `src/mr_hide/compatibility.toml`.
Candidate ranges are not release support until the current source passes every required Windows/Linux cell.

## Candidate ranges

| Client | Range | Evidence status | Note |
|---|---|---|---|
| Codex | `>=0.144.4,<0.146.0` | verified | Windows/Linux launch and resume contracts passed in GitHub Actions run 30343602093. |
| Claude Code | `>=2.1.216,<=2.1.217` | verified | Windows/Linux launch and resume contracts passed in GitHub Actions run 30343602093. |

## Required matrix

| Client | Versions | Platforms | Flow | Routes | Status |
|---|---|---|---|---|---|
| codex | 0.144.4, 0.145.0 | windows, linux | protected Responses launch and native resume | `/v1/responses` | required |
| claude | 2.1.216, 2.1.217 | windows, linux | protected Messages launch and native resume | `/v1/messages`, `/v1/messages/count_tokens` | required |

## Recorded compatibility evidence

| Date | Client | Version | Platform | Flow | Result | Limitations | Source |
|---|---|---|---|---|---|---|---|
| 2026-07-28 | codex | 0.144.4 | windows | protected Responses launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |
| 2026-07-28 | codex | 0.144.4 | linux | protected Responses launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |
| 2026-07-28 | codex | 0.145.0 | windows | protected Responses launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |
| 2026-07-28 | codex | 0.145.0 | linux | protected Responses launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |
| 2026-07-28 | claude | 2.1.216 | windows | protected Messages launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |
| 2026-07-28 | claude | 2.1.216 | linux | protected Messages launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |
| 2026-07-28 | claude | 2.1.217 | windows | protected Messages launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |
| 2026-07-28 | claude | 2.1.217 | linux | protected Messages launch and native resume | pass | Protocol-shaped local upstream and dummy credentials; live provider authentication and non-inference traffic were not exercised. | [workflow run](https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093) |

Compatibility runs use protocol-shaped local responses and dummy credentials.
Overrides
for versions outside these ranges never update this evidence or expand support.
