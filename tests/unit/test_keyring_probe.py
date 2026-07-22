from __future__ import annotations

import pytest

from mr_hide.security.keyring_probe import probe_keyring
from tests.fixtures.keyrings import ApprovedKeyring, LookalikeKeyring, RecordingKeyring


def test_unapproved_backend_fails_closed_without_writing() -> None:
    backend = RecordingKeyring()

    result = probe_keyring(backend=backend, approved_backend_types=(ApprovedKeyring,))

    assert not result.supported
    assert result.reason == "backend-not-approved"
    assert backend.calls == []


def test_backend_discovery_failure_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_discovery() -> None:
        raise RuntimeError("configuration-secret")

    monkeypatch.setattr("mr_hide.security.keyring_probe.keyring.get_keyring", fail_discovery)

    result = probe_keyring()

    assert not result.supported
    assert result.backend == "unavailable"
    assert result.reason == "probe-failed"
    assert "configuration-secret" not in repr(result)


def test_backend_type_discovery_failure_is_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = RecordingKeyring()

    def fail_discovery() -> None:
        raise RuntimeError("import-secret")

    monkeypatch.setattr(
        "mr_hide.security.keyring_probe._platform_backend_types",
        fail_discovery,
    )

    result = probe_keyring(backend=backend)

    assert not result.supported
    assert result.reason == "probe-failed"
    assert "import-secret" not in repr(result)
    assert backend.calls == []


def test_approved_backend_round_trips_and_deletes_random_sentinel() -> None:
    backend = ApprovedKeyring()

    result = probe_keyring(backend=backend, approved_backend_types=(ApprovedKeyring,))

    assert result.supported
    assert result.reason == "available"
    assert [call[0] for call in backend.calls] == ["set", "get", "delete"]
    assert backend.stored is None
    assert "ApprovedKeyring" in result.backend


def test_subclass_lookalike_is_rejected() -> None:
    backend = LookalikeKeyring()

    result = probe_keyring(backend=backend, approved_backend_types=(ApprovedKeyring,))

    assert not result.supported
    assert backend.calls == []


@pytest.mark.parametrize("failure", ("set", "get", "delete"))
def test_backend_failures_are_redacted_and_cleanup_is_attempted(failure: str) -> None:
    backend = ApprovedKeyring(fail_on=failure)

    result = probe_keyring(backend=backend, approved_backend_types=(ApprovedKeyring,))

    assert not result.supported
    assert result.reason == "probe-failed"
    assert "sentinel" not in repr(result)
    assert backend.calls[-1][0] == "delete"


def test_mismatched_round_trip_fails_and_cleans_up() -> None:
    backend = ApprovedKeyring(returned_value="wrong-value")

    result = probe_keyring(backend=backend, approved_backend_types=(ApprovedKeyring,))

    assert not result.supported
    assert result.reason == "round-trip-mismatch"
    assert backend.stored is None


def test_repeated_probes_use_distinct_test_credentials() -> None:
    first = ApprovedKeyring()
    second = ApprovedKeyring()

    probe_keyring(backend=first, approved_backend_types=(ApprovedKeyring,))
    probe_keyring(backend=second, approved_backend_types=(ApprovedKeyring,))

    assert first.calls[0][1:] != second.calls[0][1:]
