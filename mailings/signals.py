from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from mailings.models import Mailing, MailingAttempt
from mailings.statistics_cache import invalidate_user_statistics


@receiver([post_save, post_delete], sender=MailingAttempt)
def clear_statistics_on_attempt_change(sender, instance, **kwargs):
    """Сбрасывает кеш после изменения попытки отправки."""

    owner_id = (
        Mailing.objects.filter(pk=instance.mailing_id)
        .values_list("owner_id", flat=True)
        .first()
    )

    invalidate_user_statistics(owner_id)


@receiver([post_save, post_delete], sender=Mailing)
def clear_statistics_on_mailing_change(sender, instance, **kwargs):
    """Сбрасывает кеш после изменения рассылки."""

    invalidate_user_statistics(instance.owner_id)
