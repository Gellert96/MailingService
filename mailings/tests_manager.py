from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mailings.models import Mailing, MailingAttempt, Message
from mailings.services import send_mailing

User = get_user_model()


class ManagerTests(TestCase):
    """Проверяет полномочия менеджеров."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(
            email="manager@example.com",
            password="TestPassword123!",
        )

        cls.regular_user = User.objects.create_user(
            email="regular@example.com",
            password="TestPassword123!",
        )

        cls.other_manager = User.objects.create_user(
            email="another-manager@example.com",
            password="TestPassword123!",
        )

        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="TestPassword123!",
        )

        manager_group = Group.objects.create(name="Менеджеры")
        cls.manager.groups.add(manager_group)
        cls.other_manager.groups.add(manager_group)

        cls.message = Message.objects.create(
            owner=cls.regular_user,
            subject="Тестовое сообщение",
            body="Проверка полномочий менеджера.",
        )

        now = timezone.now()

        cls.mailing = Mailing.objects.create(
            owner=cls.regular_user,
            message=cls.message,
            start_time=now - timedelta(minutes=1),
            end_time=now + timedelta(hours=1),
        )

    def test_regular_user_cannot_open_dashboard(self):
        """Обычный пользователь не имеет доступа к панели."""

        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("manager_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_manager_can_open_dashboard(self):
        """Менеджер может открыть панель управления."""

        self.client.force_login(self.manager)

        response = self.client.get(reverse("manager_dashboard"))

        self.assertEqual(response.status_code, 200)

    def test_manager_can_block_and_unblock_user(self):
        """Менеджер блокирует и разблокирует пользователя."""

        self.client.force_login(self.manager)

        url = reverse(
            "manager_toggle_user",
            args=[self.regular_user.pk],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_active)

    def test_manager_cannot_block_privileged_users(self):
        """Нельзя блокировать себя, менеджеров и суперпользователей."""

        self.client.force_login(self.manager)

        protected_users = (
            self.manager,
            self.other_manager,
            self.admin,
        )

        for account in protected_users:
            with self.subTest(account=account.email):
                response = self.client.post(
                    reverse(
                        "manager_toggle_user",
                        args=[account.pk],
                    )
                )

                self.assertEqual(response.status_code, 302)

                account.refresh_from_db()
                self.assertTrue(account.is_active)

    def test_manager_can_disable_and_enable_mailing(self):
        """Менеджер может отключить и включить рассылку."""

        self.client.force_login(self.manager)

        url = reverse(
            "manager_toggle_mailing",
            args=[self.mailing.pk],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        self.mailing.refresh_from_db()
        self.assertFalse(self.mailing.is_enabled)

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        self.mailing.refresh_from_db()
        self.assertTrue(self.mailing.is_enabled)

    def test_regular_user_cannot_disable_mailing(self):
        """Обычный пользователь не может отключать рассылки."""

        self.client.force_login(self.regular_user)

        response = self.client.post(
            reverse(
                "manager_toggle_mailing",
                args=[self.mailing.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

        self.mailing.refresh_from_db()
        self.assertTrue(self.mailing.is_enabled)

    @patch("mailings.services.send_mail")
    def test_disabled_mailing_cannot_send(self, mocked_send):
        """Отключённая рассылка не отправляет письма."""

        self.mailing.is_enabled = False
        self.mailing.save(update_fields=["is_enabled"])

        with self.assertRaises(ValidationError):
            send_mailing(self.mailing)

        mocked_send.assert_not_called()

        self.assertEqual(
            MailingAttempt.objects.filter(mailing=self.mailing).count(),
            0,
        )
