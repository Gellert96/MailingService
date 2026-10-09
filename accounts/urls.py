from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path, reverse_lazy

from accounts.forms import (
    EmailLoginForm,
    EmailPasswordResetForm,
    NewPasswordForm,
)
from accounts.views import (
    ActivateAccountView,
    RegistrationDoneView,
    RegistrationView,
)

app_name = "accounts"

urlpatterns = [
    # Регистрация
    path(
        "register/",
        RegistrationView.as_view(),
        name="register",
    ),
    path(
        "register/done/",
        RegistrationDoneView.as_view(),
        name="registration_done",
    ),
    path(
        "activate/<str:uidb64>/<str:token>/",
        ActivateAccountView.as_view(),
        name="activate",
    ),
    # Вход
    path(
        "login/",
        LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailLoginForm,
        ),
        name="login",
    ),
    # Выход
    path(
        "logout/",
        LogoutView.as_view(
            next_page="home",
        ),
        name="logout",
    ),
    # Восстановление пароля
    path(
        "password-reset/",
        PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            form_class=EmailPasswordResetForm,
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirm/<str:uidb64>/<str:token>/",
        PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=NewPasswordForm,
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
