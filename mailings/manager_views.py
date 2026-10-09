from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from mailings.access import ManagerRequiredMixin, is_manager
from mailings.models import Mailing

User = get_user_model()


def can_manage_user(manager, target):
    """Проверяет, разрешено ли блокировать пользователя."""

    return (
        manager.pk != target.pk
        and not target.is_superuser
        and not target.is_staff
        and not is_manager(target)
    )


class ManagerDashboardView(ManagerRequiredMixin, TemplateView):
    """Панель управления пользователями и рассылками."""

    template_name = "mailings/manager_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        users = list(User.objects.prefetch_related("groups").order_by("email"))

        for account in users:
            account.can_be_managed = can_manage_user(
                self.request.user,
                account,
            )

        context["users"] = users

        context["mailings"] = Mailing.objects.select_related(
            "owner", "message"
        ).order_by("-start_time")

        context["users_count"] = len(users)
        context["mailings_count"] = Mailing.objects.count()

        context["enabled_mailings_count"] = Mailing.objects.filter(
            is_enabled=True
        ).count()

        return context


class ManagerToggleUserView(ManagerRequiredMixin, View):
    """Блокирует или разблокирует обычного пользователя."""

    def post(self, request, pk):
        account = get_object_or_404(User, pk=pk)

        if not can_manage_user(request.user, account):
            messages.error(
                request,
                "Нельзя изменить состояние этого аккаунта.",
            )
            return redirect("manager_dashboard")

        account.is_active = not account.is_active
        account.save(update_fields=["is_active"])

        if account.is_active:
            messages.success(
                request,
                f"Пользователь {account.email} разблокирован.",
            )
        else:
            messages.success(
                request,
                f"Пользователь {account.email} заблокирован.",
            )

        return redirect("manager_dashboard")


class ManagerToggleMailingView(ManagerRequiredMixin, View):
    """Включает или отключает рассылку."""

    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)

        mailing.is_enabled = not mailing.is_enabled
        mailing.save(update_fields=["is_enabled"])

        if mailing.is_enabled:
            messages.success(
                request,
                f"Рассылка №{mailing.pk} включена.",
            )
        else:
            messages.success(
                request,
                f"Рассылка №{mailing.pk} отключена.",
            )

        return redirect("manager_dashboard")
