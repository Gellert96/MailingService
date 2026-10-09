from django.contrib import admin

from mailings.models import Mailing, MailingAttempt, Message, Recipient


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    """Управление получателями рассылок."""

    list_display = ("id", "full_name", "email")
    search_fields = ("full_name", "email")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Управление сообщениями."""

    list_display = ("id", "subject")
    search_fields = ("subject", "body")


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    """Управление рассылками."""

    list_display = (
        "id",
        "message",
        "start_time",
        "end_time",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("message__subject",)
    filter_horizontal = ("recipients",)
    readonly_fields = ("status",)


@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    """Просмотр истории попыток отправки."""

    list_display = (
        "id",
        "mailing",
        "attempt_time",
        "status",
    )
    list_filter = ("status",)
    readonly_fields = (
        "mailing",
        "attempt_time",
        "status",
        "server_response",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Register your models here.
