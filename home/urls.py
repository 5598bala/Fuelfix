from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "customer-login/",
        views.customer_login,
        name="customer_login",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("customer-logout/", views.customer_logout, name="customer_logout"),
    path("send-otp/", views.send_otp, name="send_otp"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("spareparts/", views.spareparts, name="spareparts"),
    path("contact/", views.contact, name="contact"),
    path("google-login/", views.google_login, name="google_login"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("services/", views.services, name="services"),
    path("features/", views.features, name="features"),
    path("provider/auth/", views.provider_auth, name="provider_auth"),
    path("provider/register/", views.provider_register, name="provider_register"),
    path("provider/login/", views.provider_login, name="provider_login"),
    path("provider/logout/", views.provider_logout, name="provider_logout"),
    path(
        "provider/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/provider_password_reset_form.html",
            email_template_name="registration/provider_password_reset_email.txt",
            html_email_template_name="registration/provider_password_reset_email.html",
            subject_template_name="registration/provider_password_reset_subject.txt",
            success_url=reverse_lazy("provider_password_reset_done"),
        ),
        name="provider_password_reset",
    ),
    path(
        "provider/password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/provider_password_reset_done.html",
        ),
        name="provider_password_reset_done",
    ),
    path(
        "provider/password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/provider_password_reset_confirm.html",
            success_url=reverse_lazy("provider_password_reset_complete"),
        ),
        name="provider_password_reset_confirm",
    ),
    path(
        "provider/password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/provider_password_reset_complete.html",
        ),
        name="provider_password_reset_complete",
    ),
    path("fuel-request/", views.fuel_request, name="fuel_request"),
    path("fuel-request/<int:request_id>/pay/", views.fuel_payment_checkout, name="fuel_payment_checkout"),
    path("fuel-request/<int:request_id>/payment/verify/", views.verify_fuel_payment, name="verify_fuel_payment"),
    path("fuel-request/<int:request_id>/success/", views.fuel_request_success, name="fuel_request_success"),
    path("payments/razorpay/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
    path("mechanic-request/", views.mechanic_request, name="mechanic_request"),
    path("sos/location/update/", views.update_sos_location, name="update_sos_location"),
    path("sos/location/stop/", views.stop_sos_location, name="stop_sos_location"),
    path("sos/live/<uuid:token>/", views.sos_live_location, name="sos_live_location"),
    path("sos/live/<uuid:token>/data/", views.sos_live_location_data, name="sos_live_location_data"),
    path(
    "provider/validate/",
    views.provider_validate,
    name="provider_validate",
),
path(
    "provider/dashboard/",
    views.provider_dashboard,
    name="provider_dashboard"
),
path(
    "provider/jobs/",
    views.provider_jobs,
    name="provider_jobs",
),
path(
    "provider/jobs/<int:job_id>/<str:action>/",
    views.update_fuel_job,
    name="update_fuel_job",
),
path(
    "provider/location/update/",
    views.provider_update_location,
    name="provider_update_location",
),
path(
    "provider/availability/",
    views.provider_set_online,
    name="provider_set_online",
),
path(
    "customer/track/<uuid:token>/",
    views.customer_tracking,
    name="customer_tracking",
),
path(
    "customer/track/<uuid:token>/data/",
    views.customer_tracking_data,
    name="customer_tracking_data",
),
]