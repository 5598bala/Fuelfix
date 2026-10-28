import math
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import Provider, FuelRequest


ACTIVE_JOB_STATUSES = [
    "assigned",
    "accepted",
    "out_for_delivery",
]
PROVIDER_LOCATION_MAX_AGE = timedelta(minutes=2)


def _distance_km(latitude_a, longitude_a, latitude_b, longitude_b):
    """Return the great-circle distance between two GPS points in kilometers."""
    latitude_a, longitude_a, latitude_b, longitude_b = map(
        math.radians,
        map(float, (latitude_a, longitude_a, latitude_b, longitude_b)),
    )
    latitude_delta = latitude_b - latitude_a
    longitude_delta = longitude_b - longitude_a
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a)
        * math.cos(latitude_b)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(haversine))


def assign_provider(fuel_request_id, excluded_provider_ids=()):
    """Assign a pending fuel request to the closest online, location-ready provider.

    Only approved fuel providers with a GPS update from the last two minutes are
    considered. Distance is the primary sort; active job count and provider ID
    break ties. If the request has no GPS point, choose the least-busy eligible
    provider because a distance comparison is not possible.
    """
    with transaction.atomic():
        fuel_request = (
            FuelRequest.objects
            .select_for_update()
            .get(pk=fuel_request_id)
        )

        if fuel_request.provider_id:
            return fuel_request.provider

        if fuel_request.status != "pending":
            return None

        excluded_provider_ids = set(excluded_provider_ids or ())
        location_cutoff = timezone.now() - PROVIDER_LOCATION_MAX_AGE
        eligible_providers = list(
            Provider.objects
            .filter(
                status="approved",
                is_online=True,
                latitude__isnull=False,
                longitude__isnull=False,
                last_location_update__gte=location_cutoff,
                service_type__in=["fuel_delivery", "both"],
            )
            .exclude(id__in=excluded_provider_ids)
            .annotate(
                active_jobs=Count(
                    "fuel_requests",
                    filter=Q(fuel_requests__status__in=ACTIVE_JOB_STATUSES),
                )
            )
        )

        if not eligible_providers:
            return None

        if fuel_request.latitude is not None and fuel_request.longitude is not None:
            provider = min(
                eligible_providers,
                key=lambda candidate: (
                    _distance_km(
                        fuel_request.latitude,
                        fuel_request.longitude,
                        candidate.latitude,
                        candidate.longitude,
                    ),
                    candidate.active_jobs,
                    candidate.id,
                ),
            )
        else:
            provider = min(
                eligible_providers,
                key=lambda candidate: (candidate.active_jobs, candidate.id),
            )

        fuel_request.provider = provider
        fuel_request.status = "assigned"
        fuel_request.save(update_fields=["provider", "status"])
        return provider


def assign_pending_fuel_requests():
    """Retry unassigned requests when an eligible provider comes online."""
    pending_ids = list(
        FuelRequest.objects
        .filter(status="pending", provider__isnull=True)
        .values_list("id", flat=True)
    )
    return [assign_provider(request_id) for request_id in pending_ids]