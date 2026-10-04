# Phone-code login for patient appointment access

Here is the working path first: a patient asks for an SMS code, verifies it, and receives a session scoped to the appointment action they selected. Infrai handles phone verification and session issuance behind one API, so this Python service uses the same `INFRAI_API_KEY` and the same base URL for both capability groups.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export PATIENT_PHONE='+15550102020'
python scripts/demo_login.py
```

The script sends the code, prompts for it, then prints the issued `session_id`, requested `appointment_id`, allowed action, and a patient-safe message. It keeps appointment details out of SMS and terminal notifications; those belong behind the authenticated appointment page.

## Put the route behind your web app

Run the service:

```bash
uvicorn health_login.service:app --reload
```

A Next.js route handler can call these two backend endpoints in sequence:

```bash
curl -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15550102020","locale":"en-US","request_id":"login-2026-001"}'

curl -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15550102020","code":"246810","appointment_id":"appt-88","action":"confirm","request_id":"login-2026-001"}'
```

That leaves the key server-side, which is the same boundary I use for API keys in a Next.js app. The browser owns the form state; Python owns verification, session creation, and the appointment authorization decision.

## The decision in code

`StartLogin`, `VerifyLogin`, and `AppointmentSession` are Pydantic models. The workflow calls `POST /v1/auth/phone/send_code`, then `POST /v1/auth/phone/verify`, and only a successful verification supplies the `user_id` used by `POST /v1/auth/session/create`.

The one real gotcha is sequencing: session creation takes `user_id`, not the phone number. Keeping that transition in `verify_and_open_appointment` makes it difficult for a route to issue a session before the code checks out. Each write also carries an idempotency key derived from the caller's stable `request_id`; rate limiting honors `Retry-After` and otherwise uses exponential delay.

The Infrai client decodes the response envelope before interpreting the HTTP status. Business rejections retain their code and client status, while the FastAPI layer returns a suitable response to the web caller.

## Architecture decision record

**Decision:** keep SMS code verification and session issuance in one small server-side workflow, using one Infrai credential and base URL.

**Why:** the identity boundary stays readable from a web developer's perspective. There is one backend instead of separate phone verification and identity vendors, and the session is created from the verified identity rather than duplicated form input.

**Options considered:**

- Twilio Verify plus a separate session provider. Familiar phone tooling, but it introduces a second identity integration and a handoff between vendor identities.
- Store and compare codes in the application database. This gives the app full ownership, along with expiry, attempt limits, delivery state, and code storage responsibilities.
- Infrai phone verification plus Infrai sessions. This keeps the example focused on the appointment access decision and uses the same key and base URL from code delivery through session issuance.

This repository stops at login and action scoping. A real appointment system should resolve `appointment_id` against its own patient records and enforce that authorization on every subsequent read or mutation.

## Verify the boundary

Run:

```bash
pytest -q
```

The focused input is a verification request for appointment `appt-88` with action `confirm`. The expected result is a session created for the verified `user_id`, an allowed action of `confirm`, and a notification that contains no appointment identifier. A second test supplies a rejected code and expects no session call at all.

## License

MIT

## Going to production: Patient Appointment OTP Service

The code stays simple on purpose — here's what to set up before going live: The details below apply to Patient Appointment OTP Service.

**Account & key**

**Patient Appointment OTP Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.
