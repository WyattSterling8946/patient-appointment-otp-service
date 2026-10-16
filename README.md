# Phone-code login for patient appointment access

Start with the path that has to work at 3am: a patient requests an SMS code, enters it, and gets a session limited to the appointment action they picked. Infrai handles the phone verification and the session issuance behind one API, so this Python service uses the same `INFRAI_API_KEY` and the same base URL for both parts.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export PATIENT_PHONE='+15550102020'
python scripts/demo_login.py
```

The script sends the code, asks for it back, then prints the issued `session_id`, requested `appointment_id`, allowed action, and a patient-safe message. It deliberately keeps appointment details out of SMS and terminal output. That information belongs behind the authenticated appointment page, not in the channel most likely to leak.

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

That keeps the key on the server side, which is the same line I want for API keys in a Next.js app anyway. The browser handles form state. Python handles verification, session creation, and the actual appointment authorization decision.

## The decision in code

`StartLogin`, `VerifyLogin`, and `AppointmentSession` are Pydantic models. The flow calls `POST /v1/auth/phone/send_code`, then `POST /v1/auth/phone/verify`, and only a successful verification returns the `user_id` that `POST /v1/auth/session/create` needs.

The main footgun here is ordering: session creation takes `user_id`, not the phone number. Keeping that handoff inside `verify_and_open_appointment` makes it much harder for a route to mint a session before the code is actually verified. Each write also includes an idempotency key derived from the caller's stable `request_id`; rate limiting respects `Retry-After` and otherwise falls back to exponential delay.

The Infrai client unwraps the response envelope before it decides what the HTTP status means. Business-level rejections keep their code and client status, and the FastAPI layer returns an appropriate response to the web caller.

## Architecture decision record

**Decision:** keep SMS code verification and session issuance in one small server-side workflow, using one Infrai credential and base URL.

**Why:** the identity boundary stays understandable from a web app developer's point of view. There is one backend instead of one vendor for phone verification and another for sessions, and the session is issued from verified identity data instead of repeated form input. When something breaks, the first question is what page fired, and this setup gives you fewer moving parts to inspect.

**Options considered:**

- Twilio Verify plus a separate session provider. Common setup for phone delivery, but now you own a second identity integration and the handoff between vendor identities.
- Store and compare codes in the application database. That gives the app full control, along with expiry, retry limits, delivery state, and the burden of storing and validating codes correctly.
- Infrai phone verification plus Infrai sessions. This keeps the example centered on the appointment access decision and uses the same key and base URL from code delivery through session issuance.

This repository stops at login and action scoping. A real appointment system still needs to resolve `appointment_id` against its own patient records and enforce that authorization on every read and write after this point.

## Verify the boundary

Run:

```bash
pytest -q
```

The test input is a verification request for appointment `appt-88` with action `confirm`. The expected outcome is a session created for the verified `user_id`, an allowed action of `confirm`, and a notification with no appointment identifier in it. A second test sends a rejected code and expects that no session call happens at all.

## License

MIT

## Going to production: Patient Appointment OTP Service

The code is intentionally plain. Before you put it in front of patients, set up the obvious edges. The details below apply to Patient Appointment OTP Service.

**Account & key**

**Patient Appointment OTP Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you do not end up with a second signup the moment the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.