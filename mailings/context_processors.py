from mailings.access import is_manager


def manager_access(request):
    """Передаёт информацию о роли пользователя в шаблоны."""

    return {
        "can_access_manager": is_manager(request.user),
    }
