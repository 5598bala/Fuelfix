from .models import SOSOption


def sos_options(request):
    options = list(SOSOption.objects.filter(is_active=True))
    support = next((option for option in options if option.action == "support"), None)
    return {
        "sos_options": options,
        "sos_support_phone": support.phone if support else "",
    }
