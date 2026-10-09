from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from mailings.models import Mailing, MailingAttempt, Message, Recipient
from mailings.services import send_mailing

User = get_user_model()


class MailingServiceTests(TestCase):
    """Тесты отправки рассылок."""

    def setUp(self):
        """Создаёт пользователя, сообщение, получателей и рассылку."""

        self.user = User.objects.create_user(
            email="mailing-test@example.com",
            password="TestPassword123!",
        )

        now = timezone.now()

        self.message = Message.objects.create(
            owner=self.user,
            subject="Тестовое письмо",
            body="Проверяем отправку рассылки.",
        )

        self.recipient1 = Recipient.objects.create(
            owner=self.user,
            email="test1@example.com",
            full_name="Первый получатель",
        )

        self.recipient2 = Recipient.objects.create(
            owner=self.user,
            email="test2@example.com",
            full_name="Второй получатель",
        )

        self.mailing = Mailing.objects.create(
            owner=self.user,
            start_time=now - timedelta(minutes=1),
            end_time=now + timedelta(minutes=30),
            message=self.message,
        )

        self.mailing.recipients.set([self.recipient1, self.recipient2])

    @patch("mailings.services.send_mail", return_value=1)
    def test_successful_sending(self, mocked_send):
        """Проверяет успешную отправку двум получателям."""

        result = send_mailing(self.mailing)

        self.assertEqual(result["successful"], 2)
        self.assertEqual(result["failed"], 0)

        self.assertEqual(mocked_send.call_count, 2)

        self.assertEqual(
            MailingAttempt.objects.filter(
                mailing=self.mailing,
                status=MailingAttempt.Status.SUCCESS,
            ).count(),
            2,
        )

    @patch(
        "mailings.services.send_mail",
        side_effect=SMTPException("SMTP-сервер недоступен"),
    )
    def test_failed_sending(self, mocked_send):
        """Проверяет сохранение ошибок почтового сервера."""

        result = send_mailing(self.mailing)

        self.assertEqual(result["successful"], 0)
        self.assertEqual(result["failed"], 2)

        self.assertEqual(mocked_send.call_count, 2)

        attempts = MailingAttempt.objects.filter(mailing=self.mailing)

        self.assertEqual(attempts.count(), 2)

        for attempt in attempts:
            self.assertEqual(
                attempt.status,
                MailingAttempt.Status.FAILED,
            )

            self.assertIn(
                "SMTP-сервер недоступен",
                attempt.server_response,
            )

    @patch("mailings.services.send_mail")
    def test_sending_before_start(self, mocked_send):
        """Запрещает отправку до начала рассылки."""

        self.mailing.start_time = timezone.now() + timedelta(hours=1)
        self.mailing.end_time = timezone.now() + timedelta(hours=2)

        self.mailing.save(update_fields=["start_time", "end_time"])

        with self.assertRaises(ValidationError):
            send_mailing(self.mailing)

        mocked_send.assert_not_called()

        self.assertFalse(MailingAttempt.objects.filter(mailing=self.mailing).exists())

    @patch("mailings.services.send_mail")
    def test_sending_after_end(self, mocked_send):
        """Запрещает отправку после окончания рассылки."""

        self.mailing.start_time = timezone.now() - timedelta(hours=2)
        self.mailing.end_time = timezone.now() - timedelta(hours=1)

        self.mailing.save(update_fields=["start_time", "end_time"])

        with self.assertRaises(ValidationError):
            send_mailing(self.mailing)

        mocked_send.assert_not_called()

        self.assertFalse(MailingAttempt.objects.filter(mailing=self.mailing).exists())

    @patch("mailings.services.send_mail")
    def test_cannot_send_foreign_message(self, mocked_send):
        """Запрещает отправку сообщения другого пользователя."""

        User = get_user_model()

        other_user = User.objects.create_user(
            email="foreign-message@example.com",
            password="TestPassword123!",
        )

        other_message = Message.objects.create(
            owner=other_user,
            subject="Чужое сообщение",
            body="Текст чужого сообщения",
        )

        self.mailing.message = other_message
        self.mailing.save(update_fields=["message"])

        with self.assertRaises(ValidationError):
            send_mailing(self.mailing)

        mocked_send.assert_not_called()

        self.assertFalse(MailingAttempt.objects.filter(mailing=self.mailing).exists())

    @patch("mailings.services.send_mail")
    def test_cannot_send_to_foreign_recipient(self, mocked_send):
        """Запрещает отправку чужим получателям."""

        User = get_user_model()

        other_user = User.objects.create_user(
            email="foreign-recipient@example.com",
            password="TestPassword123!",
        )

        other_recipient = Recipient.objects.create(
            owner=other_user,
            email="foreign-contact@example.com",
            full_name="Чужой получатель",
        )

        self.mailing.recipients.add(other_recipient)

        with self.assertRaises(ValidationError):
            send_mailing(self.mailing)

        mocked_send.assert_not_called()

        self.assertFalse(MailingAttempt.objects.filter(mailing=self.mailing).exists())
