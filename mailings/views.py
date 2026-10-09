from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from mailings.access import (
    MailingFormUserMixin,
    OwnerCreateMixin,
    OwnerQuerysetMixin,
    VisibleQuerysetMixin,
)
from mailings.forms import MailingForm, MessageForm, RecipientForm
from mailings.models import Mailing, Message, Recipient
from mailings.services import send_mailing

# --------------------------------------------------
# Главная страница
# --------------------------------------------------


class HomeView(TemplateView):
    """Главная страница с персональной статистикой."""

    template_name = "mailings/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["total_mailings"] = 0
        context["active_mailings"] = 0
        context["total_recipients"] = 0

        if self.request.user.is_authenticated:
            now = timezone.now()

            user_mailings = Mailing.objects.filter(owner=self.request.user)

            context["total_mailings"] = user_mailings.count()

            context["active_mailings"] = user_mailings.filter(
                is_enabled=True,
                start_time__lte=now,
                end_time__gte=now,
            ).count()

            context["total_recipients"] = Recipient.objects.filter(
                owner=self.request.user
            ).count()

        return context


# --------------------------------------------------
# Получатели
# --------------------------------------------------


class RecipientListView(VisibleQuerysetMixin, ListView):
    """Список своих получателей или всех для менеджера."""

    model = Recipient
    template_name = "mailings/recipient_list.html"
    context_object_name = "recipients"
    paginate_by = 10


class RecipientDetailView(VisibleQuerysetMixin, DetailView):
    """Просмотр получателя с проверкой доступа."""

    model = Recipient
    template_name = "mailings/recipient_detail.html"
    context_object_name = "recipient"


class RecipientCreateView(OwnerCreateMixin, CreateView):
    """Создаёт получателя и автоматически назначает владельца."""

    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("recipient_list")


class RecipientUpdateView(OwnerQuerysetMixin, UpdateView):
    """Разрешает редактировать только своих получателей."""

    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("recipient_list")


class RecipientDeleteView(OwnerQuerysetMixin, DeleteView):
    """Разрешает удалять только своих получателей."""

    model = Recipient
    template_name = "mailings/recipient_confirm_delete.html"
    success_url = reverse_lazy("recipient_list")


# --------------------------------------------------
# Сообщения
# --------------------------------------------------


class MessageListView(VisibleQuerysetMixin, ListView):
    """Список своих сообщений или всех для менеджера."""

    model = Message
    template_name = "mailings/message_list.html"
    context_object_name = "messages"
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().order_by("pk")


class MessageDetailView(VisibleQuerysetMixin, DetailView):
    """Просмотр сообщения с проверкой доступа."""

    model = Message
    template_name = "mailings/message_detail.html"
    context_object_name = "message"


class MessageCreateView(OwnerCreateMixin, CreateView):
    """Создаёт сообщение для текущего пользователя."""

    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("message_list")


class MessageUpdateView(OwnerQuerysetMixin, UpdateView):
    """Разрешает редактировать только свои сообщения."""

    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("message_list")


class MessageDeleteView(OwnerQuerysetMixin, DeleteView):
    """Разрешает удалять только свои сообщения."""

    model = Message
    template_name = "mailings/message_confirm_delete.html"
    success_url = reverse_lazy("message_list")


# --------------------------------------------------
# Рассылки
# --------------------------------------------------


class MailingListView(VisibleQuerysetMixin, ListView):
    """Список доступных пользователю рассылок."""

    model = Mailing
    template_name = "mailings/mailing_list.html"
    context_object_name = "mailings"
    paginate_by = 10

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("message")
            .prefetch_related("recipients")
            .order_by("-start_time")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        for mailing in context["mailings"]:
            mailing.update_status()

        return context


class MailingDetailView(VisibleQuerysetMixin, DetailView):
    """Просмотр рассылки с обновлением её статуса."""

    model = Mailing
    template_name = "mailings/mailing_detail.html"
    context_object_name = "mailing"

    def get_object(self, queryset=None):
        mailing = super().get_object(queryset)
        mailing.update_status()

        return mailing


class MailingCreateView(
    MailingFormUserMixin,
    OwnerCreateMixin,
    CreateView,
):
    """Создаёт рассылку для текущего пользователя."""

    model = Mailing
    form_class = MailingForm
    template_name = "mailings/mailing_form.html"

    def get_success_url(self):
        return reverse(
            "mailing_detail",
            kwargs={"pk": self.object.pk},
        )


class MailingUpdateView(
    MailingFormUserMixin,
    OwnerQuerysetMixin,
    UpdateView,
):
    """Разрешает редактировать только свои рассылки."""

    model = Mailing
    form_class = MailingForm
    template_name = "mailings/mailing_form.html"

    def get_success_url(self):
        return reverse(
            "mailing_detail",
            kwargs={"pk": self.object.pk},
        )


class MailingDeleteView(OwnerQuerysetMixin, DeleteView):
    """Разрешает удалять только свои рассылки."""

    model = Mailing
    template_name = "mailings/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing_list")


# --------------------------------------------------
# Отправка рассылок
# --------------------------------------------------


class MailingSendView(OwnerQuerysetMixin, View):
    """Запускает только собственную рассылку пользователя."""

    def post(self, request, pk):
        mailing = get_object_or_404(
            Mailing,
            pk=pk,
            owner=request.user,
        )

        try:
            result = send_mailing(mailing)

        except ValidationError as error:
            for error_message in error.messages:
                messages.error(request, error_message)

        else:
            messages.success(
                request,
                (
                    "Рассылка обработана. "
                    f"Успешно: {result['successful']}. "
                    f"Не успешно: {result['failed']}."
                ),
            )

        return redirect("mailing_detail", pk=mailing.pk)
