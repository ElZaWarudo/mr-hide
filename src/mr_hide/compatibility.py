"""Evidence-backed client compatibility policy."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from mr_hide.diagnostics import safe_probe_environment

_VERSION_PATTERN = re.compile(r"(?<![\w.])(\d+(?:\.\d+){1,3}(?:[-+._]?[A-Za-z0-9]+)*)")


class CompatibilityError(RuntimeError):
    """Base class for safe, user-facing compatibility failures."""


class ClientNotFound(CompatibilityError):
    """Raised when a configured client executable cannot be found."""


class MalformedClientVersion(CompatibilityError):
    """Raised when a client version cannot be safely interpreted."""


class UnsupportedClientVersion(CompatibilityError):
    """Raised when a client lies outside its tested compatibility range."""


@dataclass(frozen=True, slots=True)
class ClientPolicy:
    name: str
    display_name: str
    executable: str
    version_args: tuple[str, ...]
    supported: str
    evidence_status: str
    evidence_note: str

    @property
    def specifier(self) -> SpecifierSet:
        return SpecifierSet(self.supported)


@dataclass(frozen=True, slots=True)
class CompatibilityManifest:
    schema_version: int
    clients: Mapping[str, ClientPolicy]


@dataclass(frozen=True, slots=True)
class VersionCheck:
    client: str
    executable: str
    detected: Version
    tested_range: str
    evidence_status: str
    supported: bool
    override: bool


@lru_cache(maxsize=1)
def load_manifest() -> CompatibilityManifest:
    """Load the packaged manifest without accepting external overrides."""

    resource = files("mr_hide").joinpath("compatibility.toml")
    with resource.open("rb") as handle:
        data = tomllib.load(handle)

    schema_version = data.get("schema_version")
    if schema_version != 1:
        raise CompatibilityError("Unsupported packaged compatibility manifest schema.")

    raw_clients = data.get("clients")
    if not isinstance(raw_clients, dict):
        raise CompatibilityError("Packaged compatibility manifest has no client policies.")

    policies: dict[str, ClientPolicy] = {}
    try:
        for name, raw in raw_clients.items():
            if not isinstance(name, str) or not isinstance(raw, dict):
                raise CompatibilityError("Packaged compatibility manifest is malformed.")
            policy = ClientPolicy(
                name=name,
                display_name=str(raw["display_name"]),
                executable=str(raw["executable"]),
                version_args=tuple(str(value) for value in raw["version_args"]),
                supported=str(raw["supported"]),
                evidence_status=str(raw["evidence_status"]),
                evidence_note=str(raw["evidence_note"]),
            )
            _ = policy.specifier
            policies[name] = policy
    except (InvalidSpecifier, KeyError, TypeError) as error:
        raise CompatibilityError("Packaged compatibility manifest is malformed.") from error

    return CompatibilityManifest(schema_version, MappingProxyType(policies))


def check_client_version(
    client: str,
    *,
    executable: str | None = None,
    version_args: Sequence[str] | None = None,
    allow_untested: bool = False,
    timeout: float = 10.0,
) -> VersionCheck:
    """Probe one client and enforce the packaged one-run version policy."""

    manifest = load_manifest()
    try:
        policy = manifest.clients[client]
    except KeyError as error:
        raise CompatibilityError(f"Unknown client {client!r}.") from error

    requested_executable = executable or policy.executable
    resolved = _resolve_executable(requested_executable, policy.display_name)
    probe_args = tuple(version_args) if version_args is not None else policy.version_args
    output = _run_version_probe(resolved, probe_args, policy.display_name, timeout)
    detected = _parse_stable_version(output, policy.display_name)
    supported = policy.specifier.contains(detected, prereleases=False)

    if not supported and not allow_untested:
        raise UnsupportedClientVersion(
            f"{policy.display_name} {detected} is outside the tested range "
            f"{policy.supported}; rerun with --allow-untested for this execution only."
        )

    return VersionCheck(
        client=client,
        executable=resolved,
        detected=detected,
        tested_range=policy.supported,
        evidence_status=policy.evidence_status,
        supported=supported,
        override=not supported and allow_untested,
    )


def _resolve_executable(executable: str, display_name: str) -> str:
    resolved = shutil.which(executable)
    if resolved is None:
        raise ClientNotFound(
            f"{display_name} executable {executable!r} was not found on PATH."
        )
    requested_path = Path(executable)
    if requested_path.parent == Path() and _is_implicit_current_directory_match(resolved):
        raise ClientNotFound(
            f"{display_name} executable {executable!r} was not found on the explicit PATH."
        )
    return resolved


def _is_implicit_current_directory_match(resolved: str) -> bool:
    current_directory = Path.cwd().resolve()
    if Path(resolved).resolve().parent != current_directory:
        return False
    explicit_search_directories = {
        Path(entry or os.curdir).resolve() for entry in os.get_exec_path()
    }
    return current_directory not in explicit_search_directories


def _run_version_probe(
    executable: str,
    version_args: Sequence[str],
    display_name: str,
    timeout: float,
) -> str:
    try:
        completed = subprocess.run(
            (executable, *version_args),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=safe_probe_environment(os.environ),
            timeout=timeout,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise MalformedClientVersion(
            f"Could not obtain a safe {display_name} version result."
        ) from error
    if completed.returncode != 0:
        raise MalformedClientVersion(
            f"Could not obtain a safe {display_name} version result."
        )
    return f"{completed.stdout}\n{completed.stderr}"


def _parse_stable_version(output: str, display_name: str) -> Version:
    match = _VERSION_PATTERN.search(output)
    if match is None:
        raise MalformedClientVersion(f"Could not parse a stable {display_name} version.")
    try:
        version = Version(match.group(1))
    except InvalidVersion as error:
        raise MalformedClientVersion(
            f"Could not parse a stable {display_name} version."
        ) from error
    if version.is_prerelease or version.is_devrelease:
        raise UnsupportedClientVersion(
            f"{display_name} {version} is a prerelease outside the tested range."
        )
    return version
