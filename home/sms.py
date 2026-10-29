import logging
import uuid

import requests
from django.conf import settings


API_BASE_URL = "https://new.meraotp.in/api/v1/otp"
logger = logging.getLogger(__name__)


class MeraOTPError(Exception):
    """A safe-to-report MeraOTP integration error."""



def _post(endpoint, payload, idempotency_key=None):
    api_key = getattr(settings, "MERAOTP_API_KEY", "").strip()
    if not api_key:
        raise MeraOTPError("MERAOTP_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    try:
        response = requests.post(
            f"{API_BASE_URL}/{endpoint}",
            headers=headers,
            json=payload,
            timeout=(5, 20),
        )
    except requests.RequestException as exc:
        logger.warning("MeraOTP network request failed: %s", type(exc).__name__)
        raise MeraOTPError("The OTP service is temporarily unavailable.") from exc

    try:
        body = response.json()
    except ValueError as exc:
        logger.warning("MeraOTP returned non-JSON data (HTTP %s).", response.status_code)
        raise MeraOTPError("The OTP service returned an invalid response.") from exc

    if not isinstance(body, dict):
        raise MeraOTPError("The OTP service returned an invalid response.")

    return response, body


def send_login_otp(phone, reference):
    """Ask MeraOTP to generate, send, and track a login OTP."""
    response, body = _post(
        "send",
        {
            "mobile": phone,
            "purpose": "login",
            "reference": reference,
        },
        idempotency_key=f"customer_login_{uuid.uuid4().hex}",
    )

    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    raw_message_id = data.get("message_id")
    message_id = (
        str(raw_message_id).strip()
        if isinstance(raw_message_id, (str, int))
        and not isinstance(raw_message_id, bool)
        else ""
    )
    if (
        not response.ok
        or not body.get("success")
        or not message_id
        or len(message_id) > 128
    ):
        error_code = body.get("code") or body.get("error_code") or "unknown"
        logger.warning(
            "MeraOTP rejected an OTP send request (HTTP %s, code=%s).",
            response.status_code,
            str(error_code)[:80],
        )
        raise MeraOTPError("MeraOTP could not accept the OTP request.")

    return message_id


def verify_login_otp(message_id, otp):
    """Verify a submitted OTP using MeraOTP's one-time verification result."""
    response, body = _post(
        "verify",
        {"message_id": message_id, "otp": otp},
    )
    data = body.get("data") if isinstance(body.get("data"), dict) else {}

    if response.ok and body.get("success"):
        return bool(data.get("verified"))

    # The API may report an incorrect/expired code as a non-success result.
    # Treat an explicit negative verification as a normal failed attempt.
    if data.get("verified") is False:
        return False

    error = body.get("error")
    if isinstance(error, dict):
        error_code = error.get("code") or ""
    else:
        error_code = body.get("code") or body.get("error_code") or ""
    message = body.get("message") or ""
    invalid_markers = (
        "invalid_otp",
        "otp_invalid",
        "otp_mismatch",
        "incorrect otp",
        "invalid otp",
        "otp expired",
    )
    details = f"{error_code} {message}".lower()
    if any(marker in details for marker in invalid_markers):
        return False

    logger.warning(
        "MeraOTP verification request failed (HTTP %s, code=%s).",
        response.status_code,
        str(error_code or "unknown")[:80],
    )
    raise MeraOTPError("MeraOTP could not verify the code right now.")
