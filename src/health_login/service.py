from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .appointment_access import (
    AppointmentSession,
    LoginStarted,
    StartLogin,
    VerifyLogin,
    start_login,
    verify_and_open_appointment,
)
from .infrai_client import InfraiClient, InfraiError

app = FastAPI(title="Patient appointment phone login")


def _client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code})


@app.post("/login/code", response_model=LoginStarted)
def request_login_code(body: StartLogin) -> LoginStarted:
    client = InfraiClient()
    try:
        return start_login(body, client)
    except InfraiError as error:
        raise _client_error(error) from error
    finally:
        client.close()


@app.post("/login/verify", response_model=AppointmentSession)
def verify_login(body: VerifyLogin) -> AppointmentSession:
    client = InfraiClient()
    try:
        return verify_and_open_appointment(body, client)
    except InfraiError as error:
        raise _client_error(error) from error
    finally:
        client.close()

