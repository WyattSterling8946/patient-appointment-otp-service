from typing import Any

import pytest

from health_login.appointment_access import (
    AppointmentAction,
    VerifyLogin,
    verify_and_open_appointment,
)
from health_login.infrai_client import InfraiError


class RecordingAuth:
    def __init__(self, reject_code: bool = False) -> None:
        self.reject_code = reject_code
        self.calls: list[str] = []

    def send_phone_code(
        self, *, phone: str, locale: str, idempotency_key: str
    ) -> dict[str, Any]:
        self.calls.append("send")
        return {}

    def verify_phone_code(
        self, *, phone: str, code: str, idempotency_key: str
    ) -> dict[str, Any]:
        self.calls.append("verify")
        if self.reject_code:
            raise InfraiError("rejected", {}, 400)
        return {"user_id": "patient-42"}

    def create_session(
        self, *, user_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        self.calls.append(f"session:{user_id}")
        return {"session_id": "session-42"}


def login_request() -> VerifyLogin:
    return VerifyLogin(
        phone="+15550102020",
        code="246810",
        appointment_id="appt-88",
        action=AppointmentAction.CONFIRM,
        request_id="request-88",
    )


def test_verified_phone_opens_only_the_requested_appointment_action() -> None:
    auth = RecordingAuth()

    result = verify_and_open_appointment(login_request(), auth)

    assert auth.calls == ["verify", "session:patient-42"]
    assert result.session_id == "session-42"
    assert result.allowed_action is AppointmentAction.CONFIRM
    assert "appt-88" not in result.patient_message


def test_rejected_code_never_issues_a_session() -> None:
    auth = RecordingAuth(reject_code=True)

    with pytest.raises(InfraiError):
        verify_and_open_appointment(login_request(), auth)

    assert auth.calls == ["verify"]
