from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("login/", views.PortalLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="portal/password_reset.html",
            email_template_name="emails/password_reset.txt",
            subject_template_name="emails/password_reset_subject.txt",
            success_url=reverse_lazy("portal:password_reset_done"),
        ),
        name="password_reset",
    ),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="portal/password_reset_done.html"), name="password_reset_done"),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="portal/password_reset_confirm.html", success_url=reverse_lazy("portal:password_reset_complete")),
        name="password_reset_confirm",
    ),
    path("password-reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="portal/password_reset_complete.html"), name="password_reset_complete"),
    path("profile/", views.profile, name="profile"),
    path("documents/", views.documents, name="documents"),
    path("documents/upload/<int:type_id>/", views.upload_document, name="upload_document"),
    path("documents/<int:pk>/delete/", views.delete_document, name="delete_document"),
    path("documents/<int:pk>/file/", views.document_file, name="document_file"),
    path("agreements/", views.agreements, name="agreements"),
    path("agreements/sign/<slug:slug>/", views.sign, name="sign"),
    path("agreements/<int:pk>/", views.agreement_view, name="agreement_view"),
    path("agreements/<int:pk>/pdf/", views.agreement_pdf, name="agreement_pdf"),
    path("agreements/<int:pk>/signature.png", views.signature_image, name="document_file_sig"),
    path("submit/", views.submit_application, name="submit"),
]
