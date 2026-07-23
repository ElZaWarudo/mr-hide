"""Validate every versioned GitHub Actions workflow as YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def main() -> None:
    workflows = tuple(sorted((ROOT / ".github" / "workflows").glob("*.yml")))
    if not workflows:
        raise SystemExit("no GitHub Actions workflows found")
    for workflow in workflows:
        try:
            document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as error:
            raise SystemExit(f"invalid workflow YAML: {workflow.name}") from error
        if not isinstance(document, dict):
            raise SystemExit(f"workflow is not a mapping: {workflow.name}")
    print(f"workflow-yaml: pass ({len(workflows)} files)")


if __name__ == "__main__":
    main()
