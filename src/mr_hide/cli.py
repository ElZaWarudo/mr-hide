"""Mr Hide command-line surface."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import click

from mr_hide import __version__
from mr_hide.clients import LaunchConflict, get_adapter
from mr_hide.compatibility import CompatibilityError, check_client_version, load_manifest
from mr_hide.diagnostics import environment_presence, model_presence
from mr_hide.policy import ToolPolicy
from mr_hide.privacy import PrivacyProcessingError
from mr_hide.privacy.detection import build_local_detector
from mr_hide.protocols.responses import ResponsesRuntime, ResponsesRuntimeError
from mr_hide.proxy import ProxyConfigurationError, validate_upstream_url
from mr_hide.runtime.models import SupervisorError
from mr_hide.runtime.supervisor import supervise_launch
from mr_hide.security import probe_keyring
from mr_hide.state import (
    AtomicVaultStore,
    BindingRegistry,
    MasterKeyManager,
    VaultError,
    VaultRepository,
)


class ExplicitBoundaryCommand(click.Command):
    """Remember whether the user supplied the lossless client argv boundary."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        ctx.meta["explicit_client_boundary"] = "--" in args
        return super().parse_args(ctx, args)


@click.group()
@click.version_option(__version__, prog_name="mr-hide")
def cli() -> None:
    """Validate and launch supported coding clients through a local boundary."""


def _upstream_url(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    try:
        return validate_upstream_url(value)
    except ProxyConfigurationError as error:
        raise click.BadParameter(str(error)) from error


def _launch_options(function: Any) -> Any:
    function = click.argument("client_args", nargs=-1, type=click.UNPROCESSED)(function)
    function = click.option(
        "--allow-untested",
        is_flag=True,
        help="Allow an unsupported client version for this execution only.",
    )(function)
    function = click.option(
        "--upstream",
        required=True,
        callback=_upstream_url,
        metavar="URL",
        help="Explicit HTTP(S) upstream used by the local proxy.",
    )(function)
    return function


def _tool_policy_option(
    _ctx: click.Context,
    _param: click.Parameter,
    value: str,
) -> ToolPolicy:
    return ToolPolicy(value)


def _state_directory() -> Path:
    configured = os.environ.get("MR_HIDE_STATE_DIR")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            raise VaultError("state-directory-not-absolute")
        return path
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise VaultError("state-directory-unavailable")
        return Path(base) / "mr-hide"
    base = os.environ.get("XDG_STATE_HOME")
    return (Path(base) if base else Path.home() / ".local" / "state") / "mr-hide"


def _prepare_codex_runtime(
    resume_identity: str | None,
    tool_policy: ToolPolicy,
    *,
    bypass: bool,
    accept_bypass_warning: bool,
) -> ResponsesRuntime:
    state_directory = _state_directory()
    vault_directory = state_directory / "vaults"
    repository = VaultRepository(
        AtomicVaultStore(vault_directory),
        MasterKeyManager(
            state_directory,
            service=os.environ.get("MR_HIDE_KEYRING_SERVICE", "mr-hide-vault-v1"),
        ),
    )
    return ResponsesRuntime.prepare(
        repository=repository,
        registry=BindingRegistry(state_directory),
        detector=build_local_detector(),
        policy=tool_policy,
        resume_identity=resume_identity,
        bypass=bypass,
        bypass_warning_accepted=accept_bypass_warning,
    )


def _preflight(
    ctx: click.Context,
    client: str,
    upstream: str,
    allow_untested: bool,
    client_args: Sequence[str],
    tool_policy: ToolPolicy = ToolPolicy.DEFAULT,
    bypass: bool = False,
    accept_bypass_warning: bool = False,
) -> int:
    if not ctx.meta.get("explicit_client_boundary"):
        raise click.UsageError("separate client arguments with -- (use: -- CLIENT_ARGS)", ctx)
    try:
        version = check_client_version(client, allow_untested=allow_untested)
        adapter = get_adapter(client)
        adapter.validate_client_args(client_args)
    except LaunchConflict as error:
        raise click.UsageError(str(error), ctx) from error
    except CompatibilityError as error:
        raise click.ClickException(str(error)) from error
    responses_runtime: ResponsesRuntime | None = None
    if client == "codex":
        if bypass and not accept_bypass_warning:
            raise click.UsageError(
                "--bypass requires --accept-bypass-warning.",
                ctx,
            )
        try:
            resume_identity = adapter.resume_identity(client_args)
            if "resume" in adapter.interpreted_args(client_args) and resume_identity is None:
                raise click.UsageError(
                    "Codex resume requires an explicit canonical session UUID.",
                    ctx,
                )
            responses_runtime = _prepare_codex_runtime(
                resume_identity,
                tool_policy,
                bypass=bypass,
                accept_bypass_warning=accept_bypass_warning,
            )
        except click.UsageError:
            raise
        except (PrivacyProcessingError, ResponsesRuntimeError, VaultError) as error:
            reason = getattr(error, "reason", "privacy-runtime-unavailable")
            raise click.ClickException(f"Privacy runtime unavailable ({reason}).") from None
        click.echo(
            f"conversation: {'bypassed' if responses_runtime.bypassed else 'protected'}",
            err=True,
        )
        click.echo(f"tool-policy: {tool_policy.value}", err=True)
        if tool_policy is ToolPolicy.DEFAULT:
            click.echo("warning: tool-data-unprotected", err=True)
        if responses_runtime.bypassed:
            click.echo("warning: conversation-bypass-active", err=True)
    try:
        result = asyncio.run(
            supervise_launch(
                adapter=adapter,
                executable=version.executable,
                upstream=upstream,
                client_args=client_args,
                parent_env=os.environ,
                responses_runtime=responses_runtime,
            )
        )
    except SupervisorError as error:
        raise click.ClickException(str(error)) from error
    return result.exit_code


@cli.command(
    cls=ExplicitBoundaryCommand,
    context_settings={"ignore_unknown_options": True},
)
@_launch_options
@click.option(
    "--tool-policy",
    type=click.Choice([item.value for item in ToolPolicy]),
    default=ToolPolicy.DEFAULT.value,
    show_default=True,
    callback=_tool_policy_option,
    help="Choose how provider-bound tool data is protected.",
)
@click.option("--bypass", is_flag=True, help="Bypass protection for this conversation.")
@click.option(
    "--accept-bypass-warning",
    is_flag=True,
    help="Acknowledge that bypass sends conversation data unchanged.",
)
@click.pass_context
def codex(
    ctx: click.Context,
    upstream: str,
    allow_untested: bool,
    client_args: tuple[str, ...],
    tool_policy: ToolPolicy,
    bypass: bool,
    accept_bypass_warning: bool,
) -> None:
    """Preflight Codex. Syntax: OPTIONS -- CLIENT_ARGS..."""

    ctx.exit(
        _preflight(
            ctx,
            "codex",
            upstream,
            allow_untested,
            client_args,
            tool_policy,
            bypass,
            accept_bypass_warning,
        )
    )


@cli.command(
    cls=ExplicitBoundaryCommand,
    context_settings={"ignore_unknown_options": True},
)
@_launch_options
@click.pass_context
def claude(
    ctx: click.Context,
    upstream: str,
    allow_untested: bool,
    client_args: tuple[str, ...],
) -> None:
    """Preflight Claude Code. Syntax: OPTIONS -- CLIENT_ARGS..."""

    ctx.exit(_preflight(ctx, "claude", upstream, allow_untested, client_args))


@cli.command("compatibility")
@click.option("--json-output", "as_json", is_flag=True, help="Emit stable JSON output.")
def compatibility_command(as_json: bool) -> None:
    """Show packaged client ranges and their evidence state."""

    manifest = load_manifest()
    rows = [
        {
            "client": policy.name,
            "display_name": policy.display_name,
            "tested_range": policy.supported,
            "evidence_status": policy.evidence_status,
            "evidence_note": policy.evidence_note,
        }
        for policy in manifest.clients.values()
    ]
    if as_json:
        click.echo(json.dumps({"schema_version": manifest.schema_version, "clients": rows}))
        return
    for row in rows:
        click.echo(
            f"{row['display_name']}: {row['tested_range']} "
            f"[{row['evidence_status']}]"
        )


@cli.command()
def doctor() -> None:
    """Report safe client and credential-presence diagnostics."""

    for client in load_manifest().clients:
        try:
            result = check_client_version(client)
            click.echo(f"{client}: {result.detected} ({result.evidence_status})")
        except CompatibilityError as error:
            click.echo(f"{client}: {error}")
    for item in environment_presence(os.environ):
        click.echo(f"{item.name}: {'present' if item.present else 'absent'}")
    for model in model_presence():
        click.echo(
            f"nlp_model_{model.language}: "
            f"{'available' if model.available else 'unavailable'} ({model.package})"
        )
    capability = probe_keyring()
    click.echo(
        f"secure_store: {'available' if capability.supported else 'unavailable'} "
        f"({capability.backend}; {capability.reason})"
    )


def main() -> None:
    cli(prog_name="mr-hide")
