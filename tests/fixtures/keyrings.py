from __future__ import annotations


class RecordingKeyring:
    def __init__(
        self,
        *,
        returned_value: str | None = None,
        fail_on: str | None = None,
    ) -> None:
        self.returned_value = returned_value
        self.fail_on = fail_on
        self.calls: list[tuple[str, ...]] = []
        self.stored: str | None = None

    def set_password(self, service: str, account: str, password: str) -> None:
        self.calls.append(("set", service, account))
        if self.fail_on == "set":
            raise RuntimeError("sentinel must not escape")
        self.stored = password

    def get_password(self, service: str, account: str) -> str | None:
        self.calls.append(("get", service, account))
        if self.fail_on == "get":
            raise RuntimeError("sentinel must not escape")
        return self.returned_value if self.returned_value is not None else self.stored

    def delete_password(self, service: str, account: str) -> None:
        self.calls.append(("delete", service, account))
        if self.fail_on == "delete":
            raise RuntimeError("sentinel must not escape")
        self.stored = None


class ApprovedKeyring(RecordingKeyring):
    pass


class LookalikeKeyring(ApprovedKeyring):
    pass

