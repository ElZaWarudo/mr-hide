# Release readiness

This page is generated from `src/mr_hide/compatibility.toml` and versioned release checks.

## Verdict

**Conditional local pass.** The package and privacy boundary pass locally, but
release support remains gated on current compatibility evidence; this
artifact is not a publication, tag, or support-range promotion.

## Compatibility evidence needed

The recorded client run predates changes to compatibility-sensitive source.
Run the required client matrix against this revision before release.


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
- Release support is limited to the recorded client ranges and platforms; versions
  outside those ranges remain blocked unless explicitly overridden for one run.
