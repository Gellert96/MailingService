from importlib import import_module

from django.apps import AppConfig


class MailingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mailings"

    def ready(self):
        import_module("mailings.signals")
