import base64
import hashlib
import hmac
import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class RazorpayError(Exception):
    """Raised for unavailable or unsuccessful Razorpay API operations."""


def razorpay_is_configured():
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def _auth_header():
    if not razorpay_is_configured():
        raise RazorpayError("Online payments are not configured.")
    credentials = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(credentials).decode("ascii")


def _api_request(method, path, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{RAZORPAY_API_BASE}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": _auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        raise RazorpayError("Razorpay could not complete the payment operation.") from error


def amount_in_paise(amount):
    return int(amount * 100)


def create_order(fuel_request):
    if not fuel_request.payment_amount or fuel_request.payment_amount <= 0:
        raise RazorpayError("The fuel request has no valid payment total.")
    return _api_request(
        "POST",
        "/orders",
        {
            "amount": amount_in_paise(fuel_request.payment_amount),
            "currency": "INR",
            "receipt": f"fuelreq-{fuel_request.pk}-{uuid.uuid4().hex[:12]}",
            "notes": {"fuel_request_id": str(fuel_request.pk)},
        },
    )


def verify_checkout_signature(order_id, payment_id, signature):
    if not settings.RAZORPAY_KEY_SECRET:
        return False
    message = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def verify_webhook_signature(body, signature):
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def fetch_payment(payment_id):
    return _api_request("GET", f"/payments/{payment_id}")


def capture_payment(payment_id, amount):
    return _api_request(
        "POST",
        f"/payments/{payment_id}/capture",
        {"amount": amount_in_paise(amount), "currency": "INR"},
    )