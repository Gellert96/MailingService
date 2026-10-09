from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mailings.models import Mailing, Message, Recipient

User = get_user_model()


class MailingAccessTests(TestCase):
    """Проверяет права пользователей на данные рассылок."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            email="owner@example.com",
            password="TestPassword123!",
        )

        cls.other_user = User.objects.create_user(
            email="other@example.com",
            password="TestPassword123!",
        )

        cls.message = Message.objects.create(
            owner=cls.owner,
            subject="Личное сообщение",
            body="Текст тестового сообщения",
        )

        cls.recipient = Recipient.objects.create(
            owner=cls.owner,
            email="recipient@example.com",
            full_name="Тестовый получатель",
        )

        now = timezone.now()

        cls.mailing = Mailing.objects.create(
            owner=cls.owner,
            message=cls.message,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )

        cls.mailing.recipients.add(cls.recipient)

    def test_anonymous_user_cannot_view_recipients(self):
        """Гость не может просматривать получателей."""

        response = self.client.get(reverse("recipient_list"))

        self.assertEqual(response.status_code, 302)

    def test_user_sees_only_own_data(self):
        """Чужие рассылки и получатели скрыты."""

        self.client.force_login(self.other_user)

        recipients_response = self.client.get(reverse("recipient_list"))

        mailings_response = self.client.get(reverse("mailing_list"))

        self.assertEqual(recipients_response.status_code, 200)
        self.assertEqual(mailings_response.status_code, 200)

        self.assertNotContains(
            recipients_response,
            self.recipient.email,
        )

        self.assertNotContains(
            mailings_response,
            self.message.subject,
        )

    def test_user_cannot_open_foreign_mailing(self):
        """Обычный пользователь не видит чужую рассылку."""

        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse(
                "mailing_detail",
                args=[self.mailing.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_send_foreign_mailing(self):
        """Обычный пользователь не может запускать чужую рассылку."""

        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "mailing_send",
                args=[self.mailing.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            self.mailing.attempts.count(),
            0,
        )

    def test_manager_can_view_but_cannot_edit_foreign_mailing(self):
        """Менеджер видит чужую рассылку, но не редактирует её."""

        manager_group, _ = Group.objects.get_or_create(name="Менеджеры")

        self.other_user.groups.add(manager_group)

        self.client.force_login(self.other_user)

        detail_response = self.client.get(
            reverse(
                "mailing_detail",
                args=[self.mailing.pk],
            )
        )

        update_response = self.client.get(
            reverse(
                "mailing_update",
                args=[self.mailing.pk],
            )
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(update_response.status_code, 404)
