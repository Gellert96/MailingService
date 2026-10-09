from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import FormView, TemplateView

from accounts.forms import RegistrationForm

User = get_user_model()


class RegistrationView(FormView):
    """Регистрация пользователя с подтверждением email."""

    template_name = "accounts/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("accounts:registration_done")

    def form_valid(self, form):
        """Создаёт неактивного пользователя и отправляет письмо."""

        user = form.save(commit=False)
        user.is_active = False
        user.save()

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        activation_path = reverse(
            "accounts:activate",
            kwargs={
                "uidb64": uid,
                "token": token,
            },
        )

        activation_url = self.request.build_absolute_uri(activation_path)

        subject = "Подтверждение регистрации — MailingService"

        message = (
            "Здравствуйте!\n\n"
            "Спасибо за регистрацию в MailingService.\n\n"
            "Для подтверждения электронной почты "
            "перейдите по ссылке:\n\n"
            f"{activation_url}\n\n"
            "Если вы не регистрировались на нашем сайте, "
            "проигнорируйте это письмо."
        )

        try:
            sent_count = send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except SMTPException, OSError:
            user.delete()
            form.add_error(
                None,
                "Не удалось отправить письмо подтверждения. Попробуйте ещё раз.",
            )
            return self.form_invalid(form)

        if sent_count != 1:
            user.delete()
            form.add_error(
                None,
                "Письмо подтверждения не было отправлено. Попробуйте ещё раз.",
            )
            return self.form_invalid(form)

        return super().form_valid(form)


class RegistrationDoneView(TemplateView):
    """Страница с инструкцией по подтверждению email."""

    template_name = "accounts/registration_done.html"


class ActivateAccountView(View):
    """Активирует аккаунт по одноразовой ссылке."""

    def get(self, request, uidb64, token):
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

        except TypeError, ValueError, OverflowError, User.DoesNotExist:
            user = None

        activated = False

        if (
            user is not None
            and not user.is_active
            and default_token_generator.check_token(user, token)
        ):
            user.is_active = True
            user.save(update_fields=["is_active"])
            activated = True

        return render(
            request,
            "accounts/activation_result.html",
            {"activated": activated},
        )


# Create your views here.
