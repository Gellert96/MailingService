from django.core.cache import cache
from django.db.models import Count, Q

from mailings.models import MailingAttempt

STATISTICS_CACHE_TIMEOUT = 300


def get_statistics_cache_key(user_id):
    """Создаёт отдельный ключ кеша для каждого пользователя."""
    return f"mailing_statistics:user:{user_id}"


def get_cached_statistics(user_id):
    """Возвращает статистику из кеша или базы данных."""

    cache_key = get_statistics_cache_key(user_id)

    statistics = cache.get(cache_key)

    if statistics is not None:
        return statistics

    statistics = MailingAttempt.objects.filter(mailing__owner_id=user_id).aggregate(
        total_attempts=Count("pk"),
        successful_attempts=Count(
            "pk",
            filter=Q(status=MailingAttempt.Status.SUCCESS),
        ),
        failed_attempts=Count(
            "pk",
            filter=Q(status=MailingAttempt.Status.FAILED),
        ),
    )

    cache.set(
        cache_key,
        statistics,
        timeout=STATISTICS_CACHE_TIMEOUT,
    )

    return statistics


def invalidate_user_statistics(user_id):
    """Удаляет устаревшую статистику пользователя из кеша."""

    if user_id is None:
        return

    cache.delete(get_statistics_cache_key(user_id))
