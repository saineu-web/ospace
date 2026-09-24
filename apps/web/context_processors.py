from django.conf import settings


def site(request):
    return {"SITE": settings.SITE, "SITE_URL": settings.SITE_URL}
