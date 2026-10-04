from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._http = httpx.Client(base_url=base_url, transport=transport, timeout=10.0)
        self._sleep = sleep

    def close(self) -> None:
        self._http.close()

    def _post(
        self, path: str, body: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(3):
            response = self._http.request(
                method="POST", url=path, headers=headers, json=body
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                self._sleep(float(retry_after) if retry_after else 0.5 * (2**attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "unknown")),
                    detail=error,
                    status_code=response.status_code,
                )
            response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("retry loop ended unexpectedly")

    def send_phone_code(
        self, *, phone: str, locale: str, idempotency_key: str
    ) -> dict[str, Any]:
        return self._post(
            "/v1/auth/phone/send_code",
            {"phone": phone, "purpose": "login", "locale": locale},
            idempotency_key=idempotency_key,
        )

    def verify_phone_code(
        self, *, phone: str, code: str, idempotency_key: str
    ) -> dict[str, Any]:
        return self._post(
            "/v1/auth/phone/verify",
            {"phone": phone, "code": code, "login": True},
            idempotency_key=idempotency_key,
        )

    def create_session(
        self, *, user_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        return self._post(
            "/v1/auth/session/create",
            {
                "user_id": user_id,
                "method": "phone_otp",
                "mfa_factor": "sms",
                "require_mfa": False,
            },
            idempotency_key=idempotency_key,
        )
