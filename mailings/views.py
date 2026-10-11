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
    """Главная страница с общей статистикой системы."""

    template_name = "mailings/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        now = timezone.now()

        # Актуализируем статусы всех рассылок.

        # Рассылки, которые ещё не начались
        (
            Mailing.objects.filter(start_time__gt=now)
            .exclude(status=Mailing.Status.CREATED)
            .update(status=Mailing.Status.CREATED)
        )

        # Рассылки в активном временном интервале
        (
            Mailing.objects.filter(
                start_time__lte=now,
                end_time__gte=now,
            )
            .exclude(status=Mailing.Status.RUNNING)
            .update(status=Mailing.Status.RUNNING)
        )

        # Завершённые рассылки
        (
            Mailing.objects.filter(end_time__lt=now)
            .exclude(status=Mailing.Status.COMPLETED)
            .update(status=Mailing.Status.COMPLETED)
        )

        # Общее количество рассылок всей системы
        context["total_mailings"] = Mailing.objects.count()

        # Активные и включённые рассылки
        context["active_mailings"] = Mailing.objects.filter(
            status=Mailing.Status.RUNNING,
            start_time__lte=now,
            end_time__gte=now,
            is_enabled=True,
        ).count()

        # Общее количество получателей всей системы
        context["total_recipients"] = Recipient.objects.count()

        return context


# --------------------------------------------------
# Получатели
# --------------------------------------------------


class RecipientListView(VisibleQuerysetMixin, ListView):
    """Список получателей с учётом прав доступа."""

    model = Recipient
    template_name = "mailings/recipient_list.html"
    context_object_name = "recipients"
    paginate_by = 10


class RecipientDetailView(VisibleQuerysetMixin, DetailView):
    """Просмотр отдельного получателя."""

    model = Recipient
    template_name = "mailings/recipient_detail.html"
    context_object_name = "recipient"


class RecipientCreateView(OwnerCreateMixin, CreateView):
    """Создание получателя текущим пользователем."""

    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("recipient_list")


class RecipientUpdateView(OwnerQuerysetMixin, UpdateView):
    """Редактирование только собственного получателя."""

    model = Recipient
    form_class = RecipientForm
    template_name = "mailings/recipient_form.html"
    success_url = reverse_lazy("recipient_list")


class RecipientDeleteView(OwnerQuerysetMixin, DeleteView):
    """Удаление только собственного получателя."""

    model = Recipient
    template_name = "mailings/recipient_confirm_delete.html"
    success_url = reverse_lazy("recipient_list")


# --------------------------------------------------
# Сообщения
# --------------------------------------------------


class MessageListView(VisibleQuerysetMixin, ListView):
    """Список сообщений с учётом прав доступа."""

    model = Message
    template_name = "mailings/message_list.html"
    context_object_name = "messages"
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().order_by("pk")


class MessageDetailView(VisibleQuerysetMixin, DetailView):
    """Просмотр отдельного сообщения."""

    model = Message
    template_name = "mailings/message_detail.html"
    context_object_name = "message"


class MessageCreateView(OwnerCreateMixin, CreateView):
    """Создание сообщения текущим пользователем."""

    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("message_list")


class MessageUpdateView(OwnerQuerysetMixin, UpdateView):
    """Редактирование только собственного сообщения."""

    model = Message
    form_class = MessageForm
    template_name = "mailings/message_form.html"
    success_url = reverse_lazy("message_list")


class MessageDeleteView(OwnerQuerysetMixin, DeleteView):
    """Удаление только собственного сообщения."""

    model = Message
    template_name = "mailings/message_confirm_delete.html"
    success_url = reverse_lazy("message_list")


# --------------------------------------------------
# Рассылки
# --------------------------------------------------


class MailingListView(VisibleQuerysetMixin, ListView):
    """Список рассылок с проверкой прав доступа."""

    model = Mailing
    template_name = "mailings/mailing_list.html"
    context_object_name = "mailings"
    paginate_by = 10

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("message", "owner")
            .prefetch_related("recipients")
            .order_by("-start_time")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Обновляем статусы отображаемых рассылок.
        for mailing in context["mailings"]:
            mailing.update_status()

        return context


class MailingDetailView(VisibleQuerysetMixin, DetailView):
    """Подробная информация о рассылке."""

    model = Mailing
    template_name = "mailings/mailing_detail.html"
    context_object_name = "mailing"

    def get_object(self, queryset=None):
        mailing = super().get_object(queryset)

        # Обновляем временной статус при открытии.
        mailing.update_status()

        return mailing


class MailingCreateView(
    MailingFormUserMixin,
    OwnerCreateMixin,
    CreateView,
):
    """Создание рассылки текущим пользователем."""

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
    """Редактирование только собственной рассылки."""

    model = Mailing
    form_class = MailingForm
    template_name = "mailings/mailing_form.html"

    def get_success_url(self):
        return reverse(
            "mailing_detail",
            kwargs={"pk": self.object.pk},
        )


class MailingDeleteView(OwnerQuerysetMixin, DeleteView):
    """Удаление только собственной рассылки."""

    model = Mailing
    template_name = "mailings/mailing_confirm_delete.html"
    success_url = reverse_lazy("mailing_list")


# --------------------------------------------------
# Ручная отправка рассылки
# --------------------------------------------------


class MailingSendView(OwnerQuerysetMixin, View):
    """Отправка рассылки по POST-запросу."""

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

        return redirect(
            "mailing_detail",
            pk=mailing.pk,
        )
