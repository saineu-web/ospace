from django.urls import path

from . import staff_views

app_name = "staff"

urlpatterns = [
    path("", staff_views.index, name="index"),
    path("drivers/<int:pk>/", staff_views.driver, name="driver"),
    path("drivers/<int:pk>/review/", staff_views.review_driver, name="review_driver"),
    path("documents/<int:pk>/review/", staff_views.review_document, name="review_document"),
]
