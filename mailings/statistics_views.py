from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Max, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from mailings.models import Mailing, MailingAttempt
from mailings.statistics_cache import get_cached_statistics


@method_decorator(never_cache, name="dispatch")
class MailingStatisticsView(LoginRequiredMixin, TemplateView):
    """Статистика рассылок текущего пользователя."""

    template_name = "mailings/statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        user_mailings = Mailing.objects.filter(owner=user)

        # Получаем общие показатели из серверного кеша
        totals = get_cached_statistics(user.pk)

        # Подробная таблица остаётся актуальной
        mailing_stats = (
            user_mailings.select_related("message")
            .annotate(
                total_attempts=Count("attempts"),
                successful_attempts=Count(
                    "attempts",
                    filter=Q(attempts__status=MailingAttempt.Status.SUCCESS),
                ),
                failed_attempts=Count(
                    "attempts",
                    filter=Q(attempts__status=MailingAttempt.Status.FAILED),
                ),
                last_attempt=Max("attempts__attempt_time"),
            )
            .order_by("-start_time")
        )

        context["total_mailings"] = user_mailings.count()
        context["total_attempts"] = totals["total_attempts"]
        context["successful_attempts"] = totals["successful_attempts"]
        context["failed_attempts"] = totals["failed_attempts"]
        context["sent_messages"] = totals["successful_attempts"]
        context["mailing_stats"] = mailing_stats

        return context
