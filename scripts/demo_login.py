import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from health_login.appointment_access import (  # noqa: E402
    AppointmentAction,
    StartLogin,
    VerifyLogin,
    start_login,
    verify_and_open_appointment,
)
from health_login.infrai_client import InfraiClient  # noqa: E402


def main() -> None:
    phone = os.environ.get("PATIENT_PHONE", "")
    if not phone:
        raise RuntimeError("PATIENT_PHONE is required")
    request_id = os.environ.get("LOGIN_REQUEST_ID", "appointment-demo-001")
    client = InfraiClient()
    try:
        started = start_login(
            StartLogin(phone=phone, locale="en-US", request_id=request_id), client
        )
        print(f"Code sent by {started.delivery} for {started.request_id}")
        code = input("Enter the code: ").strip()
        result = verify_and_open_appointment(
            VerifyLogin(
                phone=phone,
                code=code,
                appointment_id="appt-demo-001",
                action=AppointmentAction.VIEW,
                request_id=request_id,
            ),
            client,
        )
        print(result.model_dump_json(indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()

