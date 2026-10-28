from datetime import timedelta
# Add these imports at the top of home/models.py
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PhoneOTP(models.Model):
    phone = models.CharField(max_length=15, db_index=True)
    provider_message_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.phone} @ {self.created_at:%d-%m %H:%M}"


class Contact(models.Model):
    title = models.CharField(max_length=100, default="Get In Touch")
    subtitle = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    working_hours = models.CharField(max_length=200, blank=True)

    image = models.ImageField(
        upload_to="contact/",
        blank=True,
        null=True,
    )

    emergency_text = models.CharField(
        max_length=200,
        default="Available 24 × 7",
    )

    def __str__(self):
        return self.title


class SparePart(models.Model):
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=100)
    brand = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    image = models.ImageField(
        upload_to="spareparts/",
        blank=True,
        null=True,
    )

    stock_available = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class FuelRequest(models.Model):
    # Unique URL token for the customer tracking page
    tracking_token = models.UUIDField(
    default=uuid.uuid4,
    unique=True,
    editable=False,
)

    PAYMENT_CHOICES = [
        ("online", "Online Payment"),
        ("cod", "Cash on Delivery"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_fuel_requests",
    )
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)

    fuel_type = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=8, decimal_places=2)
    vehicle = models.CharField(max_length=100, blank=True)

    address = models.TextField()

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    preferred_date = models.DateField()
    preferred_time = models.TimeField()

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default="cod",
    )

    PAYMENT_STATUS_CHOICES = [
        ("not_required", "Not required"),
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    payment_status = models.CharField(
        max_length=16,
        choices=PAYMENT_STATUS_CHOICES,
        default="not_required",
    )
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    payment_order_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    payment_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    # NEW: Connect each fuel request to a provider
    provider = models.ForeignKey(
        "home.Provider",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fuel_requests",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",

    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request #{self.id} - {self.customer_name}"

    class Meta:
        ordering = ["-created_at"]


class FuelRate(models.Model):
    FUEL_CHOICES = [
        ("Petrol", "Petrol"),
        ("Diesel", "Diesel"),
    ]

    fuel_type = models.CharField(max_length=50, choices=FUEL_CHOICES, unique=True)
    price_per_litre = models.DecimalField(max_digits=8, decimal_places=2)
    delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Optional delivery fee added to this fuel request.",
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fuel_type"]
        verbose_name = "Fuel rate"
        verbose_name_plural = "Fuel rates"

    def __str__(self):
        return f"{self.fuel_type}: ₹{self.price_per_litre}/litre"

class Provider(models.Model):

    # Provider availability and last known GPS position
    is_online = models.BooleanField(default=False)
    latitude = models.DecimalField(
    max_digits=9, decimal_places=6, null=True, blank=True
)
    longitude = models.DecimalField(
    max_digits=9, decimal_places=6, null=True, blank=True
)
    last_location_update = models.DateTimeField(null=True, blank=True)

    SERVICE_CHOICES = [
        ("fuel_delivery", "Fuel Delivery"),
        ("mechanic", "Mechanic / Roadside Repair"),
        ("both", "Fuel Delivery & Mechanic"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_profile",
    )

    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=10, unique=True)

    service_type = models.CharField(
        max_length=30,
        choices=SERVICE_CHOICES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",

    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.status})"




class SOSOption(models.Model):
    ACTION_CHOICES = [
        ("fuel", "Request urgent fuel"),
        ("mechanic", "Request a mechanic"),
        ("support", "Call FuelFix support"),
        ("share_location", "Share my live location"),
    ]

    action = models.CharField(max_length=24, choices=ACTION_CHOICES, unique=True)
    label = models.CharField(max_length=80)
    description = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "SOS menu option"
        verbose_name_plural = "SOS menu options"

    def __str__(self):
        return self.label


class MechanicRequest(models.Model):
    STATUS_CHOICES = [
        ("new", "New request"),
        ("contacted", "Customer contacted"),
        ("in_progress", "In progress"),
        ("resolved", "Resolved"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mechanic_requests",
    )
    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    issue_description = models.TextField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Mechanic request #{self.pk} - {self.customer_name}"


class SOSLocationShare(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sos_location_shares",
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy_meters = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "SOS live location share"
        verbose_name_plural = "SOS live location shares"

    def __str__(self):
        return f"Live location {self.token}"


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customer profile: {self.user.get_username()}"
