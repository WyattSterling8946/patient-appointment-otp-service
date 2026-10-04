from __future__ import annotations

from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class AppointmentAction(str, Enum):
    VIEW = "view"
    CONFIRM = "confirm"
    RESCHEDULE = "reschedule"


class StartLogin(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    locale: str = Field(default="en-US", min_length=2, max_length=16)
    request_id: str = Field(min_length=8, max_length=100)


class VerifyLogin(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    code: str = Field(min_length=4, max_length=12)
    appointment_id: str = Field(min_length=1, max_length=100)
    action: AppointmentAction
    request_id: str = Field(min_length=8, max_length=100)


class LoginStarted(BaseModel):
    delivery: str
    request_id: str


class AppointmentSession(BaseModel):
    session_id: str
    appointment_id: str
    allowed_action: AppointmentAction
    patient_message: str


class AuthGateway(Protocol):
    def send_phone_code(
        self, *, phone: str, locale: str, idempotency_key: str
    ) -> dict[str, Any]:
        raise RuntimeError("protocol method")

    def verify_phone_code(
        self, *, phone: str, code: str, idempotency_key: str
    ) -> dict[str, Any]:
        raise RuntimeError("protocol method")

    def create_session(
        self, *, user_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        raise RuntimeError("protocol method")


def start_login(request: StartLogin, auth: AuthGateway) -> LoginStarted:
    auth.send_phone_code(
        phone=request.phone,
        locale=request.locale,
        idempotency_key=f"login-code:{request.request_id}",
    )
    return LoginStarted(delivery="sms", request_id=request.request_id)


def verify_and_open_appointment(
    request: VerifyLogin, auth: AuthGateway
) -> AppointmentSession:
    verified = auth.verify_phone_code(
        phone=request.phone,
        code=request.code,
        idempotency_key=f"login-verify:{request.request_id}",
    )
    user_id = str(verified["user_id"])
    session = auth.create_session(
        user_id=user_id,
        idempotency_key=f"login-session:{request.request_id}",
    )
    return AppointmentSession(
        session_id=str(session["session_id"]),
        appointment_id=request.appointment_id,
        allowed_action=request.action,
        patient_message="Sign-in complete. Open the secure appointment page for details.",
    )
