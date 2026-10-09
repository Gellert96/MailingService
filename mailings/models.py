from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Recipient(models.Model):
    """Получатель электронной рассылки."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_recipients",
        verbose_name="Владелец",
    )

    email = models.EmailField(
        unique=True,
        verbose_name="Email",
    )

    full_name = models.CharField(
        max_length=255,
        verbose_name="Ф. И. О.",
    )

    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий",
    )

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    class Meta:
        verbose_name = "Получатель рассылки"
        verbose_name_plural = "Получатели рассылок"
        ordering = ("full_name",)


class Message(models.Model):
    """Сообщение для электронной рассылки."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_messages",
        verbose_name="Владелец",
    )

    subject = models.CharField(
        max_length=255,
        verbose_name="Тема письма",
    )

    body = models.TextField(
        verbose_name="Тело письма",
    )

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"


class Mailing(models.Model):
    """Рассылка с временным интервалом и получателями."""

    class Status(models.TextChoices):
        CREATED = "Создана", "Создана"
        RUNNING = "Запущена", "Запущена"
        COMPLETED = "Завершена", "Завершена"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_mailings",
        verbose_name="Владелец",
    )

    start_time = models.DateTimeField(
        verbose_name="Дата и время начала отправки",
    )

    end_time = models.DateTimeField(
        verbose_name="Дата и время окончания отправки",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
        verbose_name="Статус",
    )

    is_enabled = models.BooleanField(
        default=True,
        verbose_name="Рассылка включена",
    )

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="mailings",
        verbose_name="Сообщение",
    )

    recipients = models.ManyToManyField(
        Recipient,
        related_name="mailings",
        verbose_name="Получатели",
    )

    def clean(self):
        """Проверяет корректность временного интервала рассылки."""

        super().clean()
        errors = {}

        if self.start_time and self.start_time < timezone.now():
            previous_start = None

            if self.pk:
                previous_start = (
                    type(self)
                    .objects.filter(pk=self.pk)
                    .values_list("start_time", flat=True)
                    .first()
                )

            if self._state.adding or previous_start != self.start_time:
                errors["start_time"] = "Дата начала рассылки не может быть в прошлом."

        if self.start_time and self.end_time and self.start_time >= self.end_time:
            errors["end_time"] = "Дата окончания должна быть позже даты начала."

        if errors:
            raise ValidationError(errors)

    def update_status(self):
        """Обновляет статус рассылки в зависимости от времени."""

        now = timezone.now()

        if now < self.start_time:
            new_status = self.Status.CREATED

        elif now <= self.end_time:
            new_status = self.Status.RUNNING

        else:
            new_status = self.Status.COMPLETED

        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status"])

        return self.status

    def __str__(self):
        return f"Рассылка №{self.pk} — {self.status}"

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"
        ordering = ("-start_time",)


class MailingAttempt(models.Model):
    """Результат попытки отправки электронного письма."""

    class Status(models.TextChoices):
        SUCCESS = "Успешно", "Успешно"
        FAILED = "Не успешно", "Не успешно"

    attempt_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата и время попытки",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        verbose_name="Статус",
    )

    server_response = models.TextField(
        blank=True,
        verbose_name="Ответ почтового сервера",
    )

    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Рассылка",
    )

    def __str__(self):
        return f"Попытка №{self.pk} — {self.status}"

    class Meta:
        verbose_name = "Попытка рассылки"
        verbose_name_plural = "Попытки рассылок"
        ordering = ("-attempt_time",)
