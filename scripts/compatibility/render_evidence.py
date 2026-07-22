from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "src" / "mr_hide" / "compatibility.toml"
OUTPUTS = {
    ROOT / "docs" / "compatibility.md": "compatibility",
    ROOT / "docs" / "traffic-boundary.md": "traffic",
}


def load_manifest() -> dict[str, Any]:
    with MANIFEST.open("rb") as source:
        return tomllib.load(source)


def render_compatibility(manifest: dict[str, Any]) -> str:
    lines = [
        "# Client compatibility",
        "",
        "This page is generated from `src/mr_hide/compatibility.toml`.",
        "Candidate ranges are not release support until every required Windows/Linux cell passes.",
        "",
        "## Candidate ranges",
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
            "## Recorded local evidence",
            "",
            "| Date | Client | Version | Platform | Flow | Result | Limitations |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in manifest.get("observed_evidence", []):
        lines.append(
            f"| {row['date']} | {row['client']} | {row['version']} | {row['platform']} | "
            f"{row['flow']} | {row['result']} | {row['limitations']} |"
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
            "Mr Hide RDM-001 mediates only the declared inference routes below:",
            "",
            *(f"- `{route}`" for route in mediated),
            "",
            "The listener binds only to loopback. Requests preserve bodies, raw query bytes,",
            "status,",
            "stream order, and end-to-end headers after hop-by-hop filtering.",
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
            "RDM-001 performs no Presidio detection, alias substitution, restoration,",
            "encrypted mapping",
            "storage, or privacy-complete transformation. Those capabilities begin in RDM-002.",
            "",
        ]
    )


def render(kind: str, manifest: dict[str, Any]) -> str:
    return render_compatibility(manifest) if kind == "compatibility" else render_traffic(manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    manifest = load_manifest()
    stale: list[Path] = []
    for path, kind in OUTPUTS.items():
        expected = render(kind, manifest)
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
