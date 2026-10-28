
import json
import re
import logging

import json

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import FuelRequest, Provider, FuelRate

from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    authenticate,
    login,
    logout,
)
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    PhoneOTP, SparePart, FuelRequest, Provider, MechanicRequest, SOSLocationShare, CustomerProfile,
)
from .sms import MeraOTPError, send_login_otp, verify_login_otp
from .provider_assignment import assign_provider, assign_pending_fuel_requests
from .payments import RazorpayError, amount_in_paise, capture_payment, create_order, fetch_payment, razorpay_is_configured, verify_checkout_signature, verify_webhook_signature


User = get_user_model()

PHONE_RE = re.compile(r"^[6-9]\d{9}$")

RESEND_SECONDS = 30
MAX_SENDS_PER_HOUR = 5
MAX_ATTEMPTS = 5


# =========================================================
# COMMON HELPERS
# =========================================================

def _read_json(request):
    try:
        return json.loads(request.body or "{}")
    except (ValueError, TypeError):
        return {}


def _clean_phone(raw):
    digits = re.sub(r"\D", "", str(raw or ""))

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    return digits if PHONE_RE.fullmatch(digits) else None


# =========================================================
# SEND OTP
# =========================================================

@require_POST
def send_otp(request):
    phone = _clean_phone(_read_json(request).get("phone"))

    if not phone:
        return JsonResponse({
            "ok": False,
            "error": "Enter a valid 10-digit mobile number.",
        }, status=400)

    now = timezone.now()
    last = PhoneOTP.objects.filter(phone=phone).order_by("-created_at").first()
    if last:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < RESEND_SECONDS:
            wait = int(RESEND_SECONDS - elapsed) + 1
            return JsonResponse({
                "ok": False,
                "wait": wait,
                "error": f"Please wait {wait}s before requesting another OTP.",
            }, status=429)

    sent = PhoneOTP.objects.filter(
        phone=phone,
        created_at__gte=now - timedelta(hours=1),
        provider_message_id__gt="",
    ).count()
    if sent >= MAX_SENDS_PER_HOUR:
        return JsonResponse({
            "ok": False,
            "error": "Too many OTP requests. Try again after an hour.",
        }, status=429)

    record = PhoneOTP.objects.create(phone=phone)
    try:
        message_id = send_login_otp(
            phone,
            reference=f"fuelfix_customer_login_{record.pk}",
        )
    except MeraOTPError as error:
        record.delete()
        logging.warning("MeraOTP could not send a customer login OTP: %s", error)
        if not settings.MERAOTP_API_KEY:
            return JsonResponse({
                "ok": False,
                "error": "Customer OTP login is not configured yet. Contact the site administrator.",
            }, status=503)
        return JsonResponse({
            "ok": False,
            "error": "OTP could not be sent right now. Please try again later.",
        }, status=502)

    record.provider_message_id = message_id
    record.save(update_fields=["provider_message_id"])
    request.session["customer_otp_record_id"] = record.pk

    return JsonResponse({
        "ok": True,
        "message": "OTP request accepted. Please check your phone.",
        "resend_in": RESEND_SECONDS,
    })


# =========================================================
# VERIFY OTP - CUSTOMER LOGIN
# =========================================================

@require_POST
def verify_otp(request):
    data = _read_json(request)
    phone = _clean_phone(data.get("phone"))
    otp = re.sub(r"\D", "", str(data.get("otp") or ""))

    if not phone or len(otp) != 6:
        return JsonResponse({
            "ok": False,
            "error": "Enter a valid phone number and the 6-digit OTP.",
        }, status=400)

    try:
        record_id = int(request.session.get("customer_otp_record_id"))
    except (TypeError, ValueError):
        record_id = None

    record = PhoneOTP.objects.filter(
        pk=record_id,
        phone=phone,
        is_used=False,
    ).first() if record_id else None

    if not record or not record.provider_message_id or record.is_expired():
        return JsonResponse({
            "ok": False,
            "error": "OTP expired or unavailable. Please request a new one.",
        }, status=400)

    if record.attempts >= MAX_ATTEMPTS:
        return JsonResponse({
            "ok": False,
            "error": "Too many wrong attempts. Request a new OTP.",
        }, status=429)

    try:
        verified = verify_login_otp(record.provider_message_id, otp)
    except MeraOTPError as error:
        logging.warning("MeraOTP customer OTP verification failed: %s", error)
        return JsonResponse({
            "ok": False,
            "error": "OTP verification is temporarily unavailable. Please try again.",
        }, status=502)

    record.attempts += 1
    record.save(update_fields=["attempts"])

    if not verified:
        remaining = MAX_ATTEMPTS - record.attempts
        return JsonResponse({
            "ok": False,
            "error": f"Incorrect or expired OTP. {remaining} attempt(s) left.",
        }, status=400)

    record.is_used = True
    record.save(update_fields=["is_used"])
    request.session.pop("customer_otp_record_id", None)

    user, created = User.objects.get_or_create(username=phone)
    if created:
        user.set_unusable_password()
        user.save()

    # The project has both Django's ModelBackend and django-allauth's backend
    # enabled. OTP login does not authenticate with a password, so select the
    # standard backend explicitly instead of letting login() raise when it
    # finds multiple configured backends.
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    next_url = request.session.pop("customer_next", None)
    if next_url and not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = None

    return JsonResponse({
        "ok": True,
        "redirect": next_url or "/dashboard/",
    })


# =========================================================
# HOME
# =========================================================

def home(request):
    return render(request, "home.html")


# =========================================================
# CUSTOMER LOGIN
# =========================================================

def customer_login(request):
    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        request.session["customer_next"] = next_url
    else:
        next_url = None

    if request.user.is_authenticated:
        return redirect(next_url or "dashboard")

    return render(request, "customer_login.html")


def google_login(request):
    return render(request, "google_login.html")


# =========================================================
# CUSTOMER DASHBOARD
# =========================================================

@login_required(login_url="customer_login")
def dashboard(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    profile_values = {
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
        "email": request.user.email,
        "phone": request.user.username,
        "address": profile.address,
    }

    if request.method == "POST" and request.POST.get("profile_action") == "save":
        profile_values.update({
            "first_name": request.POST.get("first_name", "").strip(),
            "last_name": request.POST.get("last_name", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "phone": request.user.username,
            "address": request.POST.get("address", "").strip(),
        })
        errors = []
        if not profile_values["first_name"]:
            errors.append("First name is required.")
        if len(profile_values["first_name"]) > 150 or len(profile_values["last_name"]) > 150:
            errors.append("Names must be 150 characters or fewer.")
        if len(profile_values["email"]) > 254:
            errors.append("Email address must be 254 characters or fewer.")
        elif profile_values["email"]:
            try:
                validate_email(profile_values["email"])
            except ValidationError:
                errors.append("Enter a valid email address.")
        if len(profile_values["address"]) > 2000:
            errors.append("Address must be 2000 characters or fewer.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            request.user.first_name = profile_values["first_name"]
            request.user.last_name = profile_values["last_name"]
            request.user.email = profile_values["email"]
            request.user.save(update_fields=["first_name", "last_name", "email"])
            profile.address = profile_values["address"]
            profile.save(update_fields=["address", "updated_at"])
            messages.success(request, "Your profile has been updated.")
            return redirect("dashboard")

    my_requests = FuelRequest.objects.filter(
        Q(customer=request.user)
        | Q(phone__in=[request.user.username, getattr(request.user, "phone", "")])
    ).distinct().order_by("-created_at")

    return render(request, "customer_dashboard.html", {
        "my_requests": my_requests,
        "profile_values": profile_values,
    })


@require_POST
def customer_logout(request):
    logout(request)
    return redirect("home")


@require_POST
def provider_logout(request):
    provider = Provider.objects.filter(user=request.user).first()
    if provider and provider.is_online:
        provider.is_online = False
        provider.save(update_fields=["is_online"])
    logout(request)
    return redirect("provider_auth")

# =========================================================
# SPARE PARTS
# =========================================================

def spareparts(request):
    parts = SparePart.objects.all()

    return render(
        request,
        "spareparts.html",
        {"parts": parts},
    )


# =========================================================
# SOS MECHANIC REQUEST AND LIVE LOCATION SHARING
# =========================================================

def mechanic_request(request):
    errors = []
    values = {
        "customer_name": request.POST.get("customer_name", "").strip(),
        "phone": request.POST.get("phone", "").strip(),
        "address": request.POST.get("address", "").strip(),
        "issue_description": request.POST.get("issue_description", "").strip(),
        "latitude": request.POST.get("latitude", "").strip(),
        "longitude": request.POST.get("longitude", "").strip(),
    }

    if request.method == "POST":
        if not values["customer_name"]:
            errors.append("Enter your name.")
        if not _clean_phone(values["phone"]):
            errors.append("Enter a valid 10-digit mobile number.")
        if not values["address"]:
            errors.append("Enter your current location or address.")
        if not values["issue_description"]:
            errors.append("Describe the vehicle problem.")

        latitude = longitude = None
        if values["latitude"] or values["longitude"]:
            try:
                latitude = Decimal(values["latitude"])
                longitude = Decimal(values["longitude"])
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                latitude = longitude = None
                errors.append("Location coordinates were invalid. Please use the location button again.")

        if not errors:
            MechanicRequest.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=values["customer_name"],
                phone=_clean_phone(values["phone"]),
                address=values["address"],
                issue_description=values["issue_description"],
                latitude=latitude,
                longitude=longitude,
            )
            return render(request, "mechanic_request_success.html")

    return render(request, "mechanic_request.html", {"values": values, "errors": errors})


@require_POST
def update_sos_location(request):
    data = _read_json(request)
    try:
        latitude = Decimal(str(data.get("latitude", ""))).quantize(Decimal("0.0000001"))
        longitude = Decimal(str(data.get("longitude", ""))).quantize(Decimal("0.0000001"))
        accuracy = Decimal(str(data.get("accuracy", ""))) if data.get("accuracy") is not None else None
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise InvalidOperation
        if accuracy is not None and accuracy < 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "The browser returned an invalid location."}, status=400)

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    share, _ = SOSLocationShare.objects.get_or_create(
        session_key=session_key,
        defaults={
            "user": request.user if request.user.is_authenticated else None,
            "latitude": latitude,
            "longitude": longitude,
            "accuracy_meters": float(accuracy) if accuracy is not None else None,
            "is_active": True,
        },
    )
    share.user = request.user if request.user.is_authenticated else None
    share.latitude = latitude
    share.longitude = longitude
    share.accuracy_meters = float(accuracy) if accuracy is not None else None
    share.is_active = True
    share.save(update_fields=["user", "latitude", "longitude", "accuracy_meters", "is_active", "updated_at"])

    live_url = request.build_absolute_uri(
        reverse("sos_live_location", kwargs={"token": share.token})
    )
    return JsonResponse({"ok": True, "share_url": live_url})


@require_POST
def stop_sos_location(request):
    if request.session.session_key:
        SOSLocationShare.objects.filter(
            session_key=request.session.session_key,
            is_active=True,
        ).update(is_active=False, updated_at=timezone.now())
    return JsonResponse({"ok": True})


def sos_live_location(request, token):
    share = get_object_or_404(SOSLocationShare, token=token)
    return render(request, "sos_live_location.html", {
        "share": share,
        "location_data_url": reverse("sos_live_location_data", kwargs={"token": token}),
        "geoapify_api_key": settings.GEOAPIFY_API_KEY,
    })


@require_GET
def sos_live_location_data(request, token):
    share = get_object_or_404(SOSLocationShare, token=token)
    if not share.is_active:
        return JsonResponse({"ok": True, "active": False, "revoked": True})
    is_fresh = share.updated_at >= timezone.now() - timedelta(seconds=75)
    return JsonResponse({
        "ok": True,
        "active": is_fresh,
        "latitude": str(share.latitude),
        "longitude": str(share.longitude),
        "accuracy": share.accuracy_meters,
        "updated_at": timezone.localtime(share.updated_at).isoformat(),
    })


# =========================================================
# CONTACT
# =========================================================

def contact(request):
    return render(request, "contact.html")


# =========================================================
# HOW IT WORKS
# =========================================================

def how_it_works(request):
    return render(request, "how_it_works.html")


# =========================================================
# SERVICES
# =========================================================

def services(request):
    return render(request, "services.html")


# =========================================================
# FEATURES
# =========================================================

def features(request):
    return render(request, "features.html")


# =========================================================
# CUSTOMER FUEL REQUEST
# =========================================================

@login_required(login_url="/customer-login/")
def fuel_request(request):
    if request.method != "POST":
        return render(request, "fuel_request.html", {
            "geoapify_api_key": settings.GEOAPIFY_API_KEY,
            "form_data": {},
        })

    customer_name = request.POST.get("customer_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    fuel_type = request.POST.get("fuel_type", "").strip()
    vehicle = request.POST.get("vehicle", "").strip()
    address = request.POST.get("address", "").strip()
    preferred_date = parse_date(request.POST.get("preferred_date", ""))
    preferred_time = parse_time(request.POST.get("preferred_time", ""))
    payment_method = request.POST.get("payment_method", "cod")

    try:
        quantity = Decimal(request.POST.get("quantity", "0"))
    except (InvalidOperation, TypeError, ValueError):
        quantity = Decimal("0")

    try:
        latitude = Decimal(request.POST["latitude"]) if request.POST.get("latitude") else None
        longitude = Decimal(request.POST["longitude"]) if request.POST.get("longitude") else None
    except (InvalidOperation, TypeError, ValueError):
        latitude = longitude = None

    valid_quantities = {Decimal("1"), Decimal("2"), Decimal("3"), Decimal("5"), Decimal("10")}
    quantity_is_valid = quantity.is_finite() and quantity in valid_quantities
    errors = []
    if not customer_name:
        errors.append("Please enter your name.")
    if not _clean_phone(phone):
        errors.append("Please enter a valid 10-digit mobile number.")
    if fuel_type not in {"Petrol", "Diesel"}:
        errors.append("Please select a valid fuel type.")
    if not quantity_is_valid:
        errors.append("Please select a valid fuel quantity.")
    if not address:
        errors.append("Please enter your delivery address.")
    if not preferred_date or not preferred_time:
        errors.append("Please select a valid date and time.")
    if payment_method not in ("online", "cod"):
        errors.append("Please select a valid payment method.")

    payment_amount = None
    if payment_method == "online":
        if not razorpay_is_configured():
            errors.append("Online payment is not configured yet. Add your Razorpay keys or choose Cash on Delivery.")
        rate = FuelRate.objects.filter(fuel_type=fuel_type, is_active=True).first()
        if rate is None:
            errors.append("Online payment is unavailable until an administrator adds an active fuel rate in Django admin.")
        elif quantity_is_valid:
            payment_amount = (rate.price_per_litre * quantity + rate.delivery_fee).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if payment_amount <= 0:
                errors.append("The configured fuel rate must produce a positive total.")

    if errors:
        for error in errors:
            messages.error(request, error)
        return render(request, "fuel_request.html", {
            "geoapify_api_key": settings.GEOAPIFY_API_KEY,
            "form_data": request.POST,
        })

    fuel_request_obj = FuelRequest.objects.create(
        customer=request.user,
        customer_name=customer_name,
        phone=phone,
        fuel_type=fuel_type,
        quantity=quantity,
        vehicle=vehicle,
        address=address,
        latitude=latitude,
        longitude=longitude,
        preferred_date=preferred_date,
        preferred_time=preferred_time,
        payment_method=payment_method,
        payment_status="pending" if payment_method == "online" else "not_required",
        payment_amount=payment_amount,
        status="pending",
    )

    if payment_method == "online":
        return redirect("fuel_payment_checkout", request_id=fuel_request_obj.pk)

    # Cash-on-delivery requests are assigned immediately; online requests wait
    # for confirmed payment before becoming visible to delivery providers.
    assign_provider(fuel_request_obj.pk)
    messages.success(request, "Your fuel request was submitted successfully.")
    return redirect("fuel_request_success", request_id=fuel_request_obj.pk)


@login_required(login_url="/customer-login/")
def fuel_payment_checkout(request, request_id):
    fuel_request_obj = get_object_or_404(
        FuelRequest,
        pk=request_id,
        customer=request.user,
        payment_method="online",
    )
    if fuel_request_obj.payment_status == "paid":
        return redirect("fuel_request_success", request_id=fuel_request_obj.pk)

    gateway_error = ""
    if not razorpay_is_configured():
        gateway_error = "Razorpay is not configured. Add the API key ID and secret to your project .env file."
    elif not fuel_request_obj.payment_amount or fuel_request_obj.payment_amount <= 0:
        gateway_error = "This request has no valid payment amount. Contact FuelFix support."
    elif not fuel_request_obj.payment_order_id:
        try:
            order = create_order(fuel_request_obj)
            order_id = order.get("id")
            if not order_id:
                raise RazorpayError("Razorpay did not return an order ID.")
            fuel_request_obj.payment_order_id = order_id
            fuel_request_obj.payment_status = "pending"
            fuel_request_obj.save(update_fields=["payment_order_id", "payment_status"])
        except RazorpayError:
            logging.exception("Could not create Razorpay order for fuel request %s", fuel_request_obj.pk)
            gateway_error = "We couldn't start checkout. Check the Razorpay configuration and try again."

    return render(
        request,
        "fuel_payment_checkout.html",
        {
            "fuel_request": fuel_request_obj,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "amount_paise": amount_in_paise(fuel_request_obj.payment_amount) if fuel_request_obj.payment_amount else 0,
            "gateway_error": gateway_error,
            "customer_email": request.user.email,
        },
    )


def _mark_fuel_request_paid(fuel_request_id, payment_id):
    with transaction.atomic():
        fuel_request_obj = FuelRequest.objects.select_for_update().get(pk=fuel_request_id)
        if fuel_request_obj.payment_status != "paid":
            fuel_request_obj.payment_status = "paid"
            fuel_request_obj.payment_id = payment_id
            fuel_request_obj.save(update_fields=["payment_status", "payment_id"])
    if fuel_request_obj.status == "pending" and not fuel_request_obj.provider_id:
        assign_provider(fuel_request_obj.pk)
    return FuelRequest.objects.get(pk=fuel_request_id)


@login_required(login_url="/customer-login/")
@require_POST
def verify_fuel_payment(request, request_id):
    fuel_request_obj = get_object_or_404(
        FuelRequest,
        pk=request_id,
        customer=request.user,
        payment_method="online",
    )
    if fuel_request_obj.payment_status == "paid":
        return JsonResponse({"ok": True, "redirect_url": reverse("fuel_request_success", kwargs={"request_id": fuel_request_obj.pk})})

    try:
        data = json.loads(request.body or "{}")
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid payment response."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"ok": False, "error": "Invalid payment response."}, status=400)
    payment_id = str(data.get("razorpay_payment_id", ""))
    order_id = str(data.get("razorpay_order_id", ""))
    signature = str(data.get("razorpay_signature", ""))
    if not re.fullmatch(r"pay_[A-Za-z0-9]+", payment_id) or not order_id or order_id != fuel_request_obj.payment_order_id:
        return JsonResponse({"ok": False, "error": "Payment order did not match this request."}, status=400)
    if not verify_checkout_signature(order_id, payment_id, signature):
        return JsonResponse({"ok": False, "error": "Payment signature could not be verified."}, status=400)

    expected_amount = amount_in_paise(fuel_request_obj.payment_amount)
    try:
        payment = fetch_payment(payment_id)
        if (
            payment.get("order_id") != fuel_request_obj.payment_order_id
            or payment.get("amount") != expected_amount
            or payment.get("currency") != "INR"
        ):
            return JsonResponse({"ok": False, "error": "Payment details do not match this fuel request."}, status=400)

        if payment.get("status") == "authorized" and not payment.get("captured"):
            try:
                payment = capture_payment(payment_id, fuel_request_obj.payment_amount)
            except RazorpayError:
                # A concurrent auto-capture can make the capture call report an error.
                payment = fetch_payment(payment_id)
        if payment.get("status") != "captured" and not payment.get("captured"):
            return JsonResponse({"ok": False, "error": "Payment is not captured yet. Please wait or retry checkout."}, status=409)
    except RazorpayError:
        logging.exception("Could not verify Razorpay payment for fuel request %s", fuel_request_obj.pk)
        return JsonResponse({"ok": False, "error": "We couldn't confirm the payment yet. Please retry shortly."}, status=502)

    _mark_fuel_request_paid(fuel_request_obj.pk, payment_id)
    return JsonResponse({"ok": True, "redirect_url": reverse("fuel_request_success", kwargs={"request_id": fuel_request_obj.pk})})


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(request.body, signature):
        return HttpResponse("Invalid webhook signature", status=400)
    try:
        event = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return HttpResponse("Invalid webhook payload", status=400)

    if not isinstance(event, dict):
        return HttpResponse("Invalid webhook payload", status=400)
    if event.get("event") != "payment.captured":
        return HttpResponse(status=200)

    payment = event.get("payload", {}).get("payment", {}).get("entity", {})
    if not isinstance(payment, dict):
        return HttpResponse("Invalid payment entity", status=400)
    order_id = payment.get("order_id")
    if not order_id:
        return HttpResponse("Missing order ID", status=400)
    fuel_request_obj = FuelRequest.objects.filter(payment_order_id=order_id).first()
    if fuel_request_obj is None:
        return HttpResponse(status=200)

    expected_amount = amount_in_paise(fuel_request_obj.payment_amount)
    if (
        payment.get("status") != "captured"
        or payment.get("amount") != expected_amount
        or payment.get("currency") != "INR"
        or not payment.get("id")
    ):
        return HttpResponse("Payment does not match fuel request", status=400)
    _mark_fuel_request_paid(fuel_request_obj.pk, payment["id"])
    return HttpResponse(status=200)


@login_required(login_url="/customer-login/")
def fuel_request_success(request, request_id):
    fuel_request_obj = get_object_or_404(
        FuelRequest,
        pk=request_id,
        customer=request.user,
    )
    if fuel_request_obj.payment_method == "online" and fuel_request_obj.payment_status != "paid":
        return redirect("fuel_payment_checkout", request_id=fuel_request_obj.pk)
    tracking_url = request.build_absolute_uri(
        reverse("customer_tracking", kwargs={"token": fuel_request_obj.tracking_token})
    )
    return render(
        request,
        "fuel_request_success.html",
        {
            "fuel_request": fuel_request_obj,
            "assigned_provider": fuel_request_obj.provider,
            "tracking_url": tracking_url,
        },
    )

def _provider_auth_redirect(mode="login"):
    """Return to the provider form and keep the relevant tab selected."""
    return redirect(f"{reverse('provider_auth')}?mode={mode}")


def provider_auth(request):
    if request.user.is_authenticated:
        provider = Provider.objects.filter(
            user=request.user
        ).first()
        if provider:
            return redirect("provider_dashboard")

    auth_mode = request.GET.get("mode", "login")
    if auth_mode not in {"login", "register"}:
        auth_mode = "login"

    return render(request, "provider_auth.html", {"auth_mode": auth_mode})


# =========================================================
# PROVIDER REGISTRATION
# =========================================================

def provider_register(request):
    if request.method != "POST":
        return _provider_auth_redirect("register")

    full_name = request.POST.get("full_name", "").strip()
    phone = _clean_phone(request.POST.get("phone"))
    email = request.POST.get("email", "").strip().lower()
    service_type = request.POST.get("service_type", "").strip()
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")
    terms_accepted = request.POST.get("terms") == "accepted"

    if not all([full_name, phone, email, service_type, password, confirm_password]):
        messages.error(request, "Please complete all required fields.")
        return _provider_auth_redirect("register")

    if len(full_name) > 120:
        messages.error(request, "Name must be 120 characters or fewer.")
        return _provider_auth_redirect("register")

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Enter a valid email address.")
        return _provider_auth_redirect("register")

    if password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return _provider_auth_redirect("register")

    try:
        validate_password(password)
    except ValidationError as error:
        for message in error.messages:
            messages.error(request, message)
        return _provider_auth_redirect("register")

    if not terms_accepted:
        messages.error(request, "Please accept the terms to create an account.")
        return _provider_auth_redirect("register")

    valid_services = {"fuel_delivery", "mechanic", "both"}
    if service_type not in valid_services:
        messages.error(request, "Please select a valid service type.")
        return _provider_auth_redirect("register")

    username_max_length = User._meta.get_field("username").max_length
    if len(email) > username_max_length:
        messages.error(request, "This email address is too long to use for sign-in.")
        return _provider_auth_redirect("register")

    if User.objects.filter(email__iexact=email).exists() or User.objects.filter(
        username__iexact=email
    ).exists():
        messages.error(request, "This email is already registered. Please sign in.")
        return _provider_auth_redirect("register")

    if Provider.objects.filter(phone=phone).exists():
        messages.error(request, "This phone number is already registered.")
        return _provider_auth_redirect("register")

    try:
        with transaction.atomic():
            # create_user hashes the password before saving it to auth_user.
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=full_name,
            )
            Provider.objects.create(
                user=user,
                full_name=full_name,
                phone=phone,
                service_type=service_type,
                status="pending",
            )
    except IntegrityError:
        messages.error(
            request,
            "An account with that email or phone number already exists.",
        )
        return _provider_auth_redirect("register")
    except Exception:
        logging.exception("Provider registration failed")
        messages.error(
            request,
            "We could not create your account. Please try again.",
        )
        return _provider_auth_redirect("register")

    authenticated_user = authenticate(
        request,
        username=email,
        password=password,
    )
    if authenticated_user is None:
        messages.success(
            request,
            "Your account was saved. Sign in to continue; provider approval "
            "is required before you can receive jobs.",
        )
        return _provider_auth_redirect("login")

    login(request, authenticated_user)
    messages.success(
        request,
        "Your provider account was created and saved. Your dashboard is ready; "
        "provider approval is required before you can receive jobs.",
    )
    return redirect("provider_dashboard")


# =========================================================
# PROVIDER LOGIN
# =========================================================

def provider_login(request):
    if request.method != "POST":
        return _provider_auth_redirect("login")

    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    if not email or not password:
        messages.error(request, "Enter both your email and password.")
        return _provider_auth_redirect("login")

    user_record = User.objects.filter(email__iexact=email).first()
    if user_record is None:
        # Supports accounts created before the email-as-username flow.
        user_record = User.objects.filter(username__iexact=email).first()

    if user_record is None:
        messages.error(request, "Invalid email or password.")
        return _provider_auth_redirect("login")

    if not user_record.is_active:
        messages.error(request, "Your account is inactive. Contact support.")
        return _provider_auth_redirect("login")

    user = authenticate(
        request,
        username=user_record.get_username(),
        password=password,
    )
    if user is None:
        messages.error(request, "Invalid email or password.")
        return _provider_auth_redirect("login")

    login(request, user)
    provider = Provider.objects.filter(user=user).first()
    if provider:
        return redirect("provider_dashboard")
    return redirect("provider_validate")


# =========================================================
# PROVIDER VERIFICATION
# =========================================================

@login_required(login_url="provider_auth")
def provider_validate(request):

    provider = Provider.objects.filter(
        user=request.user
    ).first()

    if not request.user.is_active:
        status = "inactive"
        approval = "Account inactive"
        access = "Restricted"

    elif provider is None:
        status = "pending"
        approval = "Profile required"
        access = "Restricted"

    elif provider.status == "approved":
        status = "approved"
        approval = "Approved"
        access = "Allowed"

    elif provider.status == "rejected":
        status = "rejected"
        approval = "Rejected"
        access = "Restricted"

    else:
        status = "pending"
        approval = "Pending"
        access = "Restricted"

    context = {
        "verification_status": status,
        "is_authenticated": request.user.is_authenticated,
        "approval_label": approval,
        "access_label": access,
    }

    return render(
        request,
        "provider_validation.html",
        context,
    )


# =========================================================
# PROVIDER DASHBOARD
# =========================================================

@login_required(login_url="provider_auth")
def provider_dashboard(request):
    provider = Provider.objects.filter(user=request.user).first()
    if not provider:
        return redirect("provider_validate")

    profile_errors = []
    profile_values = {
        "full_name": provider.full_name,
        "phone": provider.phone,
        "email": request.user.email,
        "service_type": provider.service_type,
    }

    if request.method == "POST" and request.POST.get("action") == "update_profile":
        full_name = request.POST.get("full_name", "").strip()
        phone_input = request.POST.get("phone", "").strip()
        phone = _clean_phone(phone_input)
        email = request.POST.get("email", "").strip().lower()
        service_type = request.POST.get("service_type", "").strip()
        profile_values = {
            "full_name": full_name,
            "phone": phone_input,
            "email": email,
            "service_type": service_type,
        }

        if not full_name:
            profile_errors.append("Enter your full name.")
        elif len(full_name) > 120:
            profile_errors.append("Your name must be 120 characters or fewer.")

        if not phone:
            profile_errors.append("Enter a valid 10-digit Indian mobile number.")
        elif Provider.objects.filter(phone=phone).exclude(pk=provider.pk).exists():
            profile_errors.append("That phone number is already used by another provider.")

        if not email:
            profile_errors.append("Enter your email address.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                profile_errors.append("Enter a valid email address.")
            if len(email) > User._meta.get_field("username").max_length:
                profile_errors.append("This email address is too long to use for sign-in.")
            if User.objects.filter(
                Q(email__iexact=email) | Q(username__iexact=email)
            ).exclude(pk=request.user.pk).exists():
                profile_errors.append("That email address is already used by another account.")

        if service_type not in {"fuel_delivery", "mechanic", "both"}:
            profile_errors.append("Choose a valid service type.")

        if not profile_errors:
            try:
                with transaction.atomic():
                    provider.full_name = full_name
                    provider.phone = phone
                    provider.service_type = service_type
                    provider.save(update_fields=["full_name", "phone", "service_type"])

                    request.user.first_name = full_name
                    request.user.email = email
                    request.user.username = email
                    request.user.save(update_fields=["first_name", "email", "username"])
            except IntegrityError:
                profile_errors.append("An account with that email or phone number already exists.")
            else:
                messages.success(request, "Your profile has been updated. Use your updated email the next time you sign in.")
                return redirect(f"{reverse('provider_dashboard')}#profile")

    if provider.status == "approved":
        jobs = FuelRequest.objects.filter(provider=provider).order_by("-created_at")
    else:
        jobs = FuelRequest.objects.none()

    has_active_delivery = jobs.filter(
        status__in=["accepted", "out_for_delivery"]
    ).exists()

    return render(
        request,
        "provider_dashboard.html",
        {
            "provider": provider,
            "jobs": jobs,
            "has_active_delivery": has_active_delivery,
            "profile_values": profile_values,
            "profile_errors": profile_errors,
        },
    )
# =========================================================
# PROVIDER JOBS
# =========================================================

@login_required(login_url="provider_auth")
def provider_jobs(request):

    provider = get_object_or_404(
        Provider,
        user=request.user,
        status="approved",
    )

    jobs = FuelRequest.objects.filter(
        provider=provider
    ).order_by("-created_at")

    has_active_delivery = jobs.filter(
        status__in=["accepted", "out_for_delivery"]
    ).exists()

    return render(
        request,
        "provider_jobs.html",
        {
            "provider": provider,
            "jobs": jobs,
            "has_active_delivery": has_active_delivery,
        },
    )


# =========================================================
# PROVIDER JOB STATUS UPDATES
# =========================================================

@login_required(login_url="provider_auth")
@require_POST
def provider_update_location(request):
    """Receive the provider's current GPS coordinates."""
    provider = get_object_or_404(
        Provider,
        user=request.user,
        status="approved",
    )

    try:
        data = json.loads(request.body)
        lat = float(data["latitude"])
        lon = float(data["longitude"])

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("GPS coordinates out of range")

    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse(
            {"ok": False, "error": "Invalid GPS coordinates"},
            status=400,
        )

    location_was_stale = (
        provider.last_location_update is None
        or provider.last_location_update < timezone.now() - timedelta(minutes=2)
    )
    provider.latitude = lat
    provider.longitude = lon
    provider.last_location_update = timezone.now()
    provider.save(update_fields=[
        "latitude",
        "longitude",
        "last_location_update",
    ])

    if provider.is_online and location_was_stale:
        assign_pending_fuel_requests()

    return JsonResponse({"ok": True})


@login_required(login_url="provider_auth")
@require_POST
def provider_set_online(request):
    """Allow an approved provider to go online or offline."""
    provider = get_object_or_404(
        Provider,
        user=request.user,
        status="approved",
    )

    try:
        data = json.loads(request.body)
        online = data.get("online")
        if not isinstance(online, bool):
            raise ValueError
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse(
            {"ok": False, "error": "Expected online: true or false"},
            status=400,
        )

    provider.is_online = online
    provider.save(update_fields=["is_online"])
    if provider.is_online:
        assign_pending_fuel_requests()

    return JsonResponse({"ok": True, "online": provider.is_online})

    # Gps location


@login_required(login_url="provider_auth")
@require_POST
def update_fuel_job(request, job_id, action):
    """Allow an approved provider to update only their assigned job."""
    provider = get_object_or_404(
        Provider,
        user=request.user,
        status="approved",
    )

    transitions = {
        ("assigned", "accept"): "accepted",
        ("assigned", "reject"): "rejected",
        ("accepted", "dispatch"): "out_for_delivery",
        ("out_for_delivery", "deliver"): "delivered",
    }

    with transaction.atomic():
        job = get_object_or_404(
            FuelRequest.objects.select_for_update(),
            pk=job_id,
            provider=provider,
        )
        new_status = transitions.get((job.status, action))
        if not new_status:
            error = "This action is not allowed for the current job status."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": error}, status=400)
            messages.error(request, error)
            return redirect("provider_jobs")

        job.status = new_status
        if action == "reject":
            job.provider = None
            job.status = "pending"
            job.save(update_fields=["provider", "status"])
        else:
            job.save(update_fields=["status"])

    if action == "reject":
        assign_provider(job.id, excluded_provider_ids=[provider.id])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "status": job.status})

    messages.success(request, f"Request #{job.id}: {job.get_status_display()}.")
    return redirect("provider_jobs")


@require_GET
def customer_tracking(request, token):
    """Render the tracking page for a request's unique token."""
    job = get_object_or_404(FuelRequest, tracking_token=token)

    return render(
        request,
        "customer_tracking.html",
        {
            "job": job,
            "geoapify_api_key": settings.GEOAPIFY_API_KEY,
        },
    )


@require_GET
def customer_tracking_data(request, token):
    """Return only the location/status needed by the tracking map."""
    job = get_object_or_404(FuelRequest, tracking_token=token)

    result = {
        "status": job.status,
        "status_display": job.get_status_display(),
        "provider_latitude": None,
        "provider_longitude": None,
        "location_updated": None,
    }

    provider = job.provider
    location_is_fresh = (
        provider
        and provider.last_location_update
        and provider.last_location_update >= timezone.now() - timedelta(minutes=2)
    )
    delivery_is_active = job.status in {"accepted", "out_for_delivery"}
    if (
        delivery_is_active
        and location_is_fresh
        and provider.latitude is not None
        and provider.longitude is not None
    ):
        result.update({
            "provider_latitude": float(provider.latitude),
            "provider_longitude": float(provider.longitude),
            "location_updated": provider.last_location_update.isoformat(),
        })

    return JsonResponse(result)
