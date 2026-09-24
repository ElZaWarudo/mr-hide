from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compatibility.evidence import (  # noqa: E402
    EvidenceSummary,
    load_evidence_manifest,
    summarize_evidence,
)

MANIFEST = ROOT / "src" / "mr_hide" / "compatibility.toml"
OUTPUTS = {
    ROOT / "docs" / "compatibility.md": "compatibility",
    ROOT / "docs" / "traffic-boundary.md": "traffic",
    ROOT / "docs" / "release-readiness.md": "release",
}

def render_compatibility(
    manifest: dict[str, Any],
    evidence: EvidenceSummary,
) -> str:
    verified = evidence.complete
    lines = [
        "# Client compatibility",
        "",
        "This page is generated from `src/mr_hide/compatibility.toml`.",
        (
            "These ranges are release-supported by the recorded Windows/Linux compatibility "
            "matrix."
            if verified
            else (
                "Candidate ranges are not release support until the current source passes "
                "every required Windows/Linux cell."
            )
        ),
        "",
        "## Supported ranges" if verified else "## Candidate ranges",
        "",
        "| Client | Range | Evidence status | Note |",
        "|---|---|---|---|",
    ]
    for client in manifest["clients"].values():
        lines.append(
            f"| {client['display_name']} | `{client['supported']}` | "
            f"{client['evidence_status']} | {client['evidence_note']} |"
        )
    lines.extend(
        [
            "",
            "## Required matrix",
            "",
            "| Client | Versions | Platforms | Flow | Routes | Status |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in manifest["compatibility_matrix"]:
        lines.append(
            f"| {row['client']} | {', '.join(row['versions'])} | "
            f"{', '.join(row['platforms'])} | {row['flow']} | "
            f"{', '.join(f'`{route}`' for route in row['routes'])} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Recorded compatibility evidence",
            "",
            "| Date | Client | Version | Platform | Flow | Result | Limitations | Source |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in manifest.get("observed_evidence", []):
        source = row.get("source")
        rendered_source = f"[workflow run]({source})" if source else "local"
        lines.append(
            f"| {row['date']} | {row['client']} | {row['version']} | {row['platform']} | "
            f"{row['flow']} | {row['result']} | {row['limitations']} | "
            f"{rendered_source} |"
        )
    lines.extend(
        [
            "",
            "Compatibility runs use protocol-shaped local responses and dummy credentials.",
            "Overrides",
            "for versions outside these ranges never update this evidence or expand support.",
            "",
        ]
    )
    return "\n".join(lines)


def render_traffic(manifest: dict[str, Any]) -> str:
    rows = manifest["compatibility_matrix"]
    mediated = sorted({route for row in rows for route in row["routes"]})
    return "\n".join(
        [
            "# Traffic boundary",
            "",
            "Mr Hide mediates only the declared inference routes below:",
            "",
            *(f"- `{route}`" for route in mediated),
            "",
            "The listener binds only to loopback. Protected routes rewrite eligible JSON fields;",
            "raw forwarding preserves bodies. Requests preserve raw query bytes,",
            "status,",
            "stream order, and end-to-end headers after hop-by-hop filtering. OpenAI",
            "Responses and Anthropic Messages request/response JSON and SSE use explicit",
            "bounded field matrices. Token-count requests use the same protected Messages",
            "representation without mutating state from structural count responses.",
            "",
            "## Outside the boundary",
            "",
            "Authentication, client login, model discovery outside declared routes,",
            "telemetry, crash",
            "reporting, update checks, plugin discovery, and provider-bound tool traffic are not",
            "intercepted merely because the inference base URL points at Mr Hide. Their exact",
            "behavior can change with client versions and is recorded as documented, observed,",
            "or unknown rather",
            "than claimed as protected.",
            "",
            "## Privacy status",
            "",
            "Supported Codex `/v1/responses` and Claude `/v1/messages` traffic use local",
            "detection, reversible substitution/restoration, encrypted conversation mappings,",
            "native resume bindings, retention, bypass, and the selected tool policy.",
            "`/v1/messages/count_tokens` shares the protected request snapshot. Unknown",
            "protocol content is preserved without recursive inspection.",
            "",
        ]
    )


def render_release_readiness(
    manifest: dict[str, Any],
    evidence: EvidenceSummary,
) -> str:
    verified = evidence.complete
    lines = [
        "# Release readiness",
        "",
        (
            "This page is generated from `src/mr_hide/compatibility.toml` and versioned "
            "release checks."
        ),
        "",
        "## Verdict",
        "",
    ]
    if verified:
        lines.extend(
            [
                "**Release-ready for v0.1.0.** The package and privacy boundary pass their",
                "deterministic gates, and every required real-client contract is recorded as",
                "passing on Windows and Linux. This artifact prepares the release; it does not",
                "create a tag or publish a GitHub Release.",
                "",
                "## Required compatibility cells",
                "",
                "All required Codex and Claude Code cells are recorded as passing on Windows",
                "and Linux.",
            ]
        )
    else:
        lines.extend(
            [
                "**Conditional local pass.** The package and privacy boundary pass locally, but",
                "release support remains gated on current compatibility evidence; this",
                "artifact is not a publication, tag, or support-range promotion.",
                "",
                "## Compatibility evidence needed",
                "",
            ]
        )
        if evidence.provenance_valid and not evidence.tested_revision_current:
            lines.extend(
                [
                    "The recorded client run predates changes to compatibility-sensitive source.",
                    "Run the required client matrix against this revision before release.",
                    "",
                ]
            )
        if evidence.pending:
            lines.extend(
                [
                    "| Client | Version | Platform |",
                    "|---|---|---|",
                    *(
                        f"| {client} | {version} | {platform} |"
                        for client, version, platform in sorted(evidence.pending)
                    ),
                ]
            )
    lines.extend(
        [
            "",
            "## Deterministic local gate",
            "",
            "```shell",
            "python scripts/check_release_readiness.py --fast",
            "python scripts/check_release_readiness.py",
            "```",
            "",
            "The full command verifies the lock, static checks, hermetic and evidence tests, alias",
            (
                "benchmark, generated documentation, dependency audit, sdist/wheel contents, "
                "and a clean"
            ),
            "wheel installation. It does not publish or mutate a remote.",
            "",
            "## Release limitations",
            "",
            "- Detection is best effort and does not guarantee discovery of every sensitive value.",
            "- Default policy leaves provider-bound tool data unprotected and reports that status.",
            (
                "- Authentication, telemetry, updates, plugins, and non-inference egress are "
                "outside the"
            ),
            "  declared inference boundary.",
            (
                "- Unknown and binary protocol data remains opaque; unsupported eligible "
                "structures fail"
            ),
            "  closed rather than receiving recursive best-guess transformation.",
            (
                "- Release support is limited to the recorded client ranges and platforms; "
                "versions"
            ),
            "  outside those ranges remain blocked unless explicitly overridden for one run.",
            "",
        ]
    )
    return "\n".join(lines)


def render(
    kind: str,
    manifest: dict[str, Any],
    evidence: EvidenceSummary,
) -> str:
    if kind == "compatibility":
        return render_compatibility(manifest, evidence)
    if kind == "traffic":
        return render_traffic(manifest)
    return render_release_readiness(manifest, evidence)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    manifest = load_evidence_manifest(MANIFEST)
    evidence = summarize_evidence(manifest, repository_root=ROOT)
    stale: list[Path] = []
    for path, kind in OUTPUTS.items():
        expected = render(kind, manifest, evidence)
        if options.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                stale.append(path)
        else:
            path.write_text(expected, encoding="utf-8")
    if stale:
        print("Generated compatibility documentation is stale.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
