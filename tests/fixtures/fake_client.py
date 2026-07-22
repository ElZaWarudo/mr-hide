from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _runtime(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime-record", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--probe-endpoint-env")
    parser.add_argument("--spawn-descendant", action="store_true")
    parser.add_argument("--ignore-termination", action="store_true")
    options, _unknown = parser.parse_known_args(argv)

    if options.ignore_termination:
        signal.signal(signal.SIGTERM, lambda *_args: None)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, lambda *_args: None)

    descendant: subprocess.Popen[bytes] | None = None
    if options.spawn_descendant:
        descendant_record = options.runtime_record.with_suffix(".descendant.json")
        descendant = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "--runtime-record",
                str(descendant_record),
                "--sleep",
                "60",
                "--ignore-termination",
            ],
        )

    probe_status: int | None = None
    endpoint = os.environ.get(options.probe_endpoint_env or "", "")
    if endpoint:
        try:
            with urllib.request.urlopen(f"{endpoint}/v1/models", timeout=3) as response:
                probe_status = response.status
        except urllib.error.HTTPError as error:
            probe_status = error.code

    options.runtime_record.write_text(
        json.dumps(
            {
                "argv": sys.argv[1:],
                "endpoint": endpoint,
                "pid": os.getpid(),
                "descendant_pid": descendant.pid if descendant is not None else None,
                "probe_status": probe_status,
            }
        ),
        encoding="utf-8",
    )
    if options.sleep:
        time.sleep(options.sleep)
    return options.exit_code


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--version":
        print(f"fake-client {sys.argv[2]}")
        return 0
    if len(sys.argv) >= 2 and sys.argv[1] == "--version-bytes":
        sys.stdout.buffer.write(b"fake-client \xff\xfe\n")
        return 0
    if "--runtime-record" in sys.argv:
        return _runtime(sys.argv[1:])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
