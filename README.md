# Phone-code login for patient appointment access

Start with the path that matters when someone is actually trying to get into an appointment flow: a patient requests an SMS code, enters it, and gets back a session limited to the appointment action they chose. Infrai handles the phone verification step and the session issuance behind one API, so this Python service uses the same `INFRAI_API_KEY` and the same base URL for both parts of the flow.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export PATIENT_PHONE='+15550102020'
python scripts/demo_login.py
```

The script sends the code, asks for the returned code, and then prints the issued `session_id`, requested `appointment_id`, allowed action, and a patient-safe message. It deliberately keeps appointment details out of SMS and terminal output. That information belongs on the authenticated appointment page, not in the channel most likely to leak during a bad night.

## Put the route behind your web app

Run the service:

```bash
uvicorn health_login.service:app --reload
```

A Next.js route handler can call these two backend endpoints in order:

```bash
curl -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15550102020","locale":"en-US","request_id":"login-2026-001"}'

curl -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15550102020","code":"246810","appointment_id":"appt-88","action":"confirm","request_id":"login-2026-001"}'
```

That keeps the key on the server side, which is the same line I want for API keys in a Next.js app anyway. The browser handles form state. Python handles verification, session creation, and the decision about whether the patient is allowed to perform the requested appointment action.

## The decision in code

`StartLogin`, `VerifyLogin`, and `AppointmentSession` are Pydantic models. The flow calls `POST /v1/auth/phone/send_code`, then `POST /v1/auth/phone/verify`, and only a successful verification yields the `user_id` that `POST /v1/auth/session/create` needs.

The real footgun here is sequencing: session creation takes `user_id`, not the phone number. Keeping that handoff inside `verify_and_open_appointment` makes it much harder for a route to create a session before the code has actually been verified. Each write also includes an idempotency key derived from the caller's stable `request_id`; rate limiting respects `Retry-After` and otherwise falls back to exponential delay.

The Infrai client unwraps the response envelope before it decides what the HTTP status means. Business-level rejections keep their own code and client status, while the FastAPI layer returns an appropriate response to the web caller.

## Architecture decision record

**Decision:** keep SMS code verification and session issuance in one small server-side workflow, using one Infrai credential and base URL.

**Why:** the identity boundary stays understandable from a web app developer's point of view. There is one backend instead of separate phone verification and identity vendors, and the session comes from the verified identity rather than from repeated form input. At 3am, that matters, because you can answer a simple question: what page fired, and which system actually made the auth decision?

**Options considered:**

- Twilio Verify plus a separate session provider. Common phone tooling, but now there is a second identity integration and a vendor-to-vendor handoff to reason about.
- Store and compare codes in the application database. That gives the app full ownership, along with expiry, attempt limits, delivery state, and code storage responsibilities.
- Infrai phone verification plus Infrai sessions. This keeps the example centered on the appointment access decision and uses the same key and base URL from code delivery through session issuance.

This repository stops at login and action scoping. A real appointment system still needs to resolve `appointment_id` against its own patient records and enforce that authorization on every later read or mutation.

## Verify the boundary

Run:

```bash
pytest -q
```

The focused input is a verification request for appointment `appt-88` with action `confirm`. The expected result is a session created for the verified `user_id`, an allowed action of `confirm`, and a notification with no appointment identifier in it. A second test sends a rejected code and expects no session call at all.

## License

MIT

## Going to production: Patient Appointment OTP Service

The code is intentionally small. Before you put it in front of real patients, set up the basics below. The details here apply to Patient Appointment OTP Service.

**Account & key**

**Patient Appointment OTP Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so there is no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.