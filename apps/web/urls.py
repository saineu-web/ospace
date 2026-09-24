from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("drivers/", views.drivers, name="drivers"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("app/", views.app, name="app"),
    path("families/", views.families, name="families"),
    path("about/", views.about, name="about"),
    path("media/", views.media, name="media"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy, name="privacy"),
    path("thanks/", views.thanks, name="thanks"),
    path("robots.txt", views.robots, name="robots"),
    path("healthz", views.healthz, name="healthz"),
    # Old Wix URLs → new pages (keeps inbound links and Google results working)
    path("requirements-to-become-a-driver", RedirectView.as_view(pattern_name="web:drivers", permanent=True)),
    path("our-app", RedirectView.as_view(pattern_name="web:app", permanent=True)),
    path("blank-1", RedirectView.as_view(pattern_name="web:how_it_works", permanent=True)),
    path("team-1", RedirectView.as_view(pattern_name="web:media", permanent=True)),
    path("blank-2", RedirectView.as_view(pattern_name="web:drivers", permanent=True)),
    path("blank-5", RedirectView.as_view(pattern_name="web:about", permanent=True)),
    path("book-online", RedirectView.as_view(pattern_name="web:families", permanent=True)),
    path("privacy-policy", RedirectView.as_view(pattern_name="web:privacy", permanent=True)),
]
