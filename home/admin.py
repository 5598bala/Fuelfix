from django.contrib import admin
from .models import SparePart
from .models import FuelRequest, FuelRate
from .models import Provider, SOSOption, MechanicRequest, SOSLocationShare


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "vehicle_type",
        "brand",
        "price",
        "stock_available",
        "is_popular",
    )


@admin.register(FuelRate)
class FuelRateAdmin(admin.ModelAdmin):
    list_display = ("fuel_type", "price_per_litre", "delivery_fee", "is_active", "updated_at")
    list_display_links = ("fuel_type",)
    list_editable = ("price_per_litre", "delivery_fee", "is_active")
    list_filter = ("is_active", "fuel_type")
    readonly_fields = ("updated_at",)
# This is Fuel fix Request

@admin.register(FuelRequest)
class FuelRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "phone",
        "fuel_type",
        "quantity",
        "payment_method",
        "payment_status",
        "payment_amount",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "fuel_type",
        "created_at",
    )

    search_fields = (
        "customer_name",
        "phone",
        "address",
        "payment_order_id",
        "payment_id",
    )

    readonly_fields = ("created_at", "payment_status", "payment_amount", "payment_order_id", "payment_id")

    ordering = ("-created_at",)


# Approvel Admin code



@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email")


@admin.register(SOSOption)
class SOSOptionAdmin(admin.ModelAdmin):
    list_display = ("display_order", "action", "label", "phone", "is_active")
    list_display_links = ("action",)
    list_editable = ("display_order", "label", "phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label", "phone")
    ordering = ("display_order", "id")


@admin.register(MechanicRequest)
class MechanicRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "phone", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name", "phone", "address", "issue_description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(SOSLocationShare)
class SOSLocationShareAdmin(admin.ModelAdmin):
    list_display = ("token", "user", "is_active", "latitude", "longitude", "updated_at")
    list_filter = ("is_active", "updated_at")
    search_fields = ("token", "session_key", "user__username", "user__email")
    readonly_fields = ("token", "session_key", "user", "started_at", "updated_at")
    ordering = ("-updated_at",)
