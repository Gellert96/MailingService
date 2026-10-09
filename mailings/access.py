from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)


def is_manager(user):
    """Проверяет, является ли пользователь менеджером."""

    if not user.is_authenticated:
        return False

    return user.is_superuser or user.groups.filter(name="Менеджеры").exists()


class OwnerQuerysetMixin(LoginRequiredMixin):
    """Разрешает доступ только к собственным объектам."""

    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset.filter(owner=self.request.user)


class VisibleQuerysetMixin(LoginRequiredMixin):
    """Менеджер видит все объекты, пользователь — только свои."""

    def get_queryset(self):
        queryset = super().get_queryset()

        if is_manager(self.request.user):
            return queryset

        return queryset.filter(owner=self.request.user)


class OwnerCreateMixin(LoginRequiredMixin):
    """Автоматически назначает владельца новому объекту."""

    def form_valid(self, form):
        form.instance.owner = self.request.user

        return super().form_valid(form)


class MailingFormUserMixin:
    """Передаёт текущего пользователя в форму рассылки."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user

        return kwargs


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Разрешает доступ только менеджерам и суперпользователям."""

    def test_func(self):
        return is_manager(self.request.user)
