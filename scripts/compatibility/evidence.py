from __future__ import annotations

import hashlib
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CompatibilityCell = tuple[str, str, str, str]
PendingCell = tuple[str, str, str]
SENSITIVE_COMPATIBILITY_PATHS = (
    ".github/workflows/compatibility.yml",
    "pyproject.toml",
    "uv.lock",
    ":(glob)src/mr_hide/**/*.py",
    "tests/compatibility/conftest.py",
    ":(glob)tests/compatibility/test_*_contract.py",
    "tests/fixtures/client_contracts.py",
)
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}", re.IGNORECASE)
_SHA256 = re.compile(r"[0-9a-f]{64}", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class EvidenceSummary:
    required: frozenset[CompatibilityCell]
    observed_passes: frozenset[CompatibilityCell]
    clients_verified: bool
    matrix_matches_verified_clients: bool
    provenance_valid: bool
    tested_revision_current: bool

    @property
    def complete(self) -> bool:
        return (
            bool(self.required)
            and self.required <= self.observed_passes
            and self.clients_verified
            and self.matrix_matches_verified_clients
            and self.provenance_valid
            and self.tested_revision_current
        )

    @property
    def pending(self) -> frozenset[PendingCell]:
        return frozenset(
            (client, version, platform)
            for client, version, platform, _flow in self.required
            - self.observed_passes
        )


def load_evidence_manifest(path: Path) -> dict[str, Any]:
    with path.open("rb") as source:
        return tomllib.load(source)


def summarize_evidence(
    manifest: dict[str, Any],
    *,
    repository_root: Path | None = None,
) -> EvidenceSummary:
    try:
        clients = manifest["clients"]
        matrix = manifest["compatibility_matrix"]
        registered_clients = frozenset(clients)
        verified_clients = frozenset(
            name
            for name, client in clients.items()
            if client["evidence_status"] == "verified"
        )
        matrix_clients = frozenset(row["client"] for row in matrix)
        required = frozenset(
            (row["client"], version, platform, row["flow"])
            for row in matrix
            for version in row["versions"]
            for platform in row["platforms"]
        )
        observed_passes = frozenset(
            (row["client"], row["version"], row["platform"], row["flow"])
            for row in manifest.get("observed_evidence", [])
            if row["result"] == "pass"
        )
    except (KeyError, TypeError):
        return _incomplete_summary()

    run_id, head_sha, sensitive_tree_sha256, source = _run_provenance(manifest)
    passing_rows = [
        row
        for row in manifest.get("observed_evidence", [])
        if row.get("result") == "pass"
    ]
    provenance_valid = bool(passing_rows) and (
        bool(run_id)
        and _COMMIT_SHA.fullmatch(head_sha) is not None
        and _SHA256.fullmatch(sensitive_tree_sha256) is not None
        and source.startswith("https://")
        and source.rstrip("/").endswith(f"/runs/{run_id}")
        and all(row.get("source") == source for row in passing_rows)
    )
    return EvidenceSummary(
        required=required,
        observed_passes=observed_passes,
        clients_verified=bool(registered_clients)
        and registered_clients == verified_clients,
        matrix_matches_verified_clients=bool(matrix)
        and matrix_clients == verified_clients,
        provenance_valid=provenance_valid,
        tested_revision_current=repository_root is not None
        and provenance_valid
        and _tested_revision_is_current(repository_root, sensitive_tree_sha256),
    )


def _run_provenance(manifest: dict[str, Any]) -> tuple[str, str, str, str]:
    try:
        evidence_run = manifest["evidence_run"]
        return (
            str(evidence_run["run_id"]),
            str(evidence_run["head_sha"]),
            str(evidence_run["sensitive_tree_sha256"]),
            str(evidence_run["source"]),
        )
    except (KeyError, TypeError):
        return "", "", "", ""


def _tested_revision_is_current(
    repository_root: Path,
    sensitive_tree_sha256: str,
) -> bool:
    if _sensitive_index_sha256(repository_root) != sensitive_tree_sha256.casefold():
        return False

    unstaged_changes = subprocess.run(
        ("git", "diff", "--quiet", "--", *SENSITIVE_COMPATIBILITY_PATHS),
        cwd=repository_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if unstaged_changes.returncode != 0:
        return False

    untracked = subprocess.run(
        (
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            *SENSITIVE_COMPATIBILITY_PATHS,
        ),
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return untracked.returncode == 0 and not untracked.stdout.strip()


def _sensitive_index_sha256(repository_root: Path) -> str | None:
    staged = subprocess.run(
        (
            "git",
            "ls-files",
            "--stage",
            "-z",
            "--",
            *SENSITIVE_COMPATIBILITY_PATHS,
        ),
        cwd=repository_root,
        check=False,
        capture_output=True,
    )
    if staged.returncode != 0:
        return None

    entries: list[tuple[bytes, bytes]] = []
    try:
        for record in staged.stdout.split(b"\0"):
            if not record:
                continue
            metadata, path = record.split(b"\t", maxsplit=1)
            _mode, blob_sha, stage = metadata.split()
            if stage != b"0":
                return None
            entries.append((path, blob_sha))
    except ValueError:
        return None
    if not entries:
        return None

    canonical = b"".join(
        path + b"\0" + blob_sha + b"\n"
        for path, blob_sha in sorted(entries)
    )
    return hashlib.sha256(canonical).hexdigest()


def _incomplete_summary() -> EvidenceSummary:
    return EvidenceSummary(
        required=frozenset(),
        observed_passes=frozenset(),
        clients_verified=False,
        matrix_matches_verified_clients=False,
        provenance_valid=False,
        tested_revision_current=False,
    )
