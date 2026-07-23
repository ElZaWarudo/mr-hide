# Release readiness

This page is generated from `src/mr_hide/compatibility.toml` and versioned release checks.

## Verdict

**Conditional local pass.** The package, privacy boundary, and recorded Windows client
contracts pass locally. MVP release support remains gated on the required Linux cells
below; this artifact is not a publication, tag, or support-range promotion.

## Required cells not observed locally

| Client | Version | Platform |
|---|---|---|
| claude | 2.1.216 | linux |
| claude | 2.1.217 | linux |
| codex | 0.144.4 | linux |
| codex | 0.145.0 | linux |

## Deterministic local gate

```shell
python scripts/check_release_readiness.py --fast
python scripts/check_release_readiness.py
```

The full command verifies the lock, static checks, hermetic and evidence tests, alias
benchmark, generated documentation, dependency audit, sdist/wheel contents, and a clean
wheel installation. It does not publish or mutate a remote.

## Release limitations

- Detection is best effort and does not guarantee discovery of every sensitive value.
- Default policy leaves provider-bound tool data unprotected and reports that status.
- Authentication, telemetry, updates, plugins, and non-inference egress are outside the
  declared inference boundary.
- Unknown and binary protocol data remains opaque; unsupported eligible structures fail
  closed rather than receiving recursive best-guess transformation.
- Candidate client ranges do not become release support until every required workflow
  cell passes on its declared operating system.
