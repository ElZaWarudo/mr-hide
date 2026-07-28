from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from scripts.compatibility.evidence import (
    SENSITIVE_COMPATIBILITY_PATHS,
    summarize_evidence,
)


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _tested_repository(tmp_path: Path) -> tuple[Path, str, str]:
    repository = tmp_path / "repository"
    source = repository / "src" / "mr_hide" / "compatibility.py"
    source.parent.mkdir(parents=True)
    source.write_text("TESTED = True\n", encoding="utf-8")
    _git(repository, "init")
    _git(repository, "add", str(source.relative_to(repository)))
    _git(
        repository,
        "-c",
        "user.name=Compatibility Test",
        "-c",
        "user.email=compatibility@example.invalid",
        "commit",
        "-m",
        "tested revision",
    )
    return (
        repository,
        _git(repository, "rev-parse", "HEAD"),
        _sensitive_tree_sha256(repository),
    )


def _sensitive_tree_sha256(repository: Path) -> str:
    staged = subprocess.run(
        (
            "git",
            "ls-files",
            "--stage",
            "-z",
            "--",
            *SENSITIVE_COMPATIBILITY_PATHS,
        ),
        cwd=repository,
        check=True,
        capture_output=True,
    ).stdout
    entries: list[tuple[bytes, bytes]] = []
    for record in staged.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", maxsplit=1)
        _mode, blob_sha, _stage = metadata.split()
        entries.append((path, blob_sha))
    canonical = b"".join(
        path + b"\0" + blob_sha + b"\n"
        for path, blob_sha in sorted(entries)
    )
    return hashlib.sha256(canonical).hexdigest()


def _manifest(head_sha: str, sensitive_tree_sha256: str) -> dict[str, Any]:
    source = "https://github.com/ElZaWarudo/mr-hide/actions/runs/30343602093"
    flow = "protected Responses launch and native resume"
    return {
        "clients": {"codex": {"evidence_status": "verified"}},
        "compatibility_matrix": [
            {
                "client": "codex",
                "versions": ["0.145.0"],
                "platforms": ["windows"],
                "flow": flow,
            }
        ],
        "evidence_run": {
            "run_id": "30343602093",
            "head_sha": head_sha,
            "sensitive_tree_sha256": sensitive_tree_sha256,
            "source": source,
        },
        "observed_evidence": [
            {
                "client": "codex",
                "version": "0.145.0",
                "platform": "windows",
                "flow": flow,
                "result": "pass",
                "source": source,
            }
        ],
    }


def test_wrong_flow_does_not_complete_required_cell(tmp_path: Path) -> None:
    repository, head_sha, tree_sha = _tested_repository(tmp_path)
    manifest = _manifest(head_sha, tree_sha)
    manifest["observed_evidence"][0]["flow"] = "version probe only"

    assert summarize_evidence(manifest, repository_root=repository).complete is False


def test_empty_clients_fail_closed(tmp_path: Path) -> None:
    repository, head_sha, tree_sha = _tested_repository(tmp_path)
    manifest = _manifest(head_sha, tree_sha)
    manifest["clients"] = {}

    assert summarize_evidence(manifest, repository_root=repository).complete is False


def test_empty_matrix_fails_closed(tmp_path: Path) -> None:
    repository, head_sha, tree_sha = _tested_repository(tmp_path)
    manifest = _manifest(head_sha, tree_sha)
    manifest["compatibility_matrix"] = []

    assert summarize_evidence(manifest, repository_root=repository).complete is False


def test_verified_client_without_matrix_row_fails_closed(tmp_path: Path) -> None:
    repository, head_sha, tree_sha = _tested_repository(tmp_path)
    manifest = _manifest(head_sha, tree_sha)
    manifest["clients"]["claude"] = {"evidence_status": "verified"}

    assert summarize_evidence(manifest, repository_root=repository).complete is False


def test_missing_immutable_run_revision_fails_closed(tmp_path: Path) -> None:
    repository, head_sha, tree_sha = _tested_repository(tmp_path)
    manifest = _manifest(head_sha, tree_sha)
    del manifest["evidence_run"]["head_sha"]

    assert summarize_evidence(manifest, repository_root=repository).complete is False


def test_manifest_only_change_keeps_recorded_run_current(tmp_path: Path) -> None:
    repository, head_sha, tree_sha = _tested_repository(tmp_path)
    manifest_path = repository / "src" / "mr_hide" / "compatibility.toml"
    manifest_path.write_text("evidence = 'recorded after run'\n", encoding="utf-8")

    assert (
        summarize_evidence(
            _manifest(head_sha, tree_sha),
            repository_root=repository,
        ).complete
        is True
    )


def test_sensitive_compatibility_change_invalidates_recorded_run(tmp_path: Path) -> None:
    repository, head_sha, tree_sha = _tested_repository(tmp_path)
    source = repository / "src" / "mr_hide" / "compatibility.py"
    source.write_text("TESTED = False\n", encoding="utf-8")

    summary = summarize_evidence(
        manifest=_manifest(head_sha, tree_sha),
        repository_root=repository,
    )

    assert summary.complete is False


def test_shallow_clone_accepts_matching_sensitive_index_tree(tmp_path: Path) -> None:
    repository, tested_sha, tree_sha = _tested_repository(tmp_path)
    evidence = repository / "docs" / "evidence.md"
    evidence.parent.mkdir()
    evidence.write_text("Recorded after the compatibility run.\n", encoding="utf-8")
    _git(repository, "add", str(evidence.relative_to(repository)))
    _git(
        repository,
        "-c",
        "user.name=Compatibility Test",
        "-c",
        "user.email=compatibility@example.invalid",
        "commit",
        "-m",
        "record evidence",
    )
    shallow = tmp_path / "shallow"
    _git(tmp_path, "clone", "--depth", "1", repository.as_uri(), str(shallow))
    missing_commit = subprocess.run(
        ("git", "cat-file", "-e", f"{tested_sha}^{{commit}}"),
        cwd=shallow,
        check=False,
        capture_output=True,
    )

    assert missing_commit.returncode != 0
    assert (
        summarize_evidence(
            _manifest(tested_sha, tree_sha),
            repository_root=shallow,
        ).complete
        is True
    )
