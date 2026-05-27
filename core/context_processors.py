from .models import SiteMessage


def site_message(request):
    msgs = SiteMessage.objects.filter(is_active=True).order_by("-updated_at")
    return {"site_messages": msgs}
