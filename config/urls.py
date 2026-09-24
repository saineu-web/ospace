from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.web.sitemaps import StaticSitemap

admin.site.site_header = "Ospace administration"
admin.site.site_title = "Ospace admin"
admin.site.index_title = "Drivers, documents & website"

urlpatterns = [
    path("", include("apps.web.urls")),
    path("portal/", include("apps.portal.urls")),
    path("staff/", include("apps.portal.staff_urls")),
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": {"static": StaticSitemap}}, name="sitemap"),
    path("internal/pulse/", __import__("django_pulse").pulse_view),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
