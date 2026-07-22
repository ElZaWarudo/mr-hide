"""Mr Hide command-line surface."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

import click

from mr_hide import __version__
from mr_hide.clients import LaunchConflict, get_adapter
from mr_hide.compatibility import CompatibilityError, check_client_version, load_manifest
from mr_hide.diagnostics import environment_presence


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
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise click.BadParameter("must be an http(s) URL without userinfo or a fragment")
    return value


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


def _preflight(
    ctx: click.Context,
    client: str,
    upstream: str,
    allow_untested: bool,
    client_args: Sequence[str],
) -> None:
    if not ctx.meta.get("explicit_client_boundary"):
        raise click.UsageError("separate client arguments with -- (use: -- CLIENT_ARGS)", ctx)
    try:
        result = check_client_version(client, allow_untested=allow_untested)
        get_adapter(client).validate_client_args(client_args)
    except LaunchConflict as error:
        raise click.UsageError(str(error), ctx) from error
    except CompatibilityError as error:
        raise click.ClickException(str(error)) from error
    status = "unsupported one-run override" if result.override else result.evidence_status
    raise click.ClickException(
        f"{client} {result.detected} preflight passed ({status}) with an explicit upstream; "
        "the supervised local proxy runtime is not available in this foundation slice."
    )


@cli.command(
    cls=ExplicitBoundaryCommand,
    context_settings={"ignore_unknown_options": True},
)
@_launch_options
@click.pass_context
def codex(
    ctx: click.Context,
    upstream: str,
    allow_untested: bool,
    client_args: tuple[str, ...],
) -> None:
    """Preflight Codex. Syntax: OPTIONS -- CLIENT_ARGS..."""

    _preflight(ctx, "codex", upstream, allow_untested, client_args)


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

    _preflight(ctx, "claude", upstream, allow_untested, client_args)


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


def main() -> None:
    cli(prog_name="mr-hide")
