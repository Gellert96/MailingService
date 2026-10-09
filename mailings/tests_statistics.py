from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mailings.models import Mailing, MailingAttempt, Message

User = get_user_model()


class StatisticsTests(TestCase):
    """Проверяет статистику и разграничение доступа."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="stats@example.com",
            password="TestPassword123!",
        )

        cls.other_user = User.objects.create_user(
            email="other-stats@example.com",
            password="TestPassword123!",
        )

        cls.empty_user = User.objects.create_user(
            email="empty@example.com",
            password="TestPassword123!",
        )

        message = Message.objects.create(
            owner=cls.user,
            subject="Моя рассылка",
            body="Тестовое сообщение",
        )

        other_message = Message.objects.create(
            owner=cls.other_user,
            subject="Чужая рассылка",
            body="Другое сообщение",
        )

        now = timezone.now()

        cls.mailing = Mailing.objects.create(
            owner=cls.user,
            message=message,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )

        other_mailing = Mailing.objects.create(
            owner=cls.other_user,
            message=other_message,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )

        for _ in range(2):
            MailingAttempt.objects.create(
                mailing=cls.mailing,
                status=MailingAttempt.Status.SUCCESS,
                server_response="Успешно",
            )

        MailingAttempt.objects.create(
            mailing=cls.mailing,
            status=MailingAttempt.Status.FAILED,
            server_response="Ошибка SMTP",
        )

        MailingAttempt.objects.create(
            mailing=other_mailing,
            status=MailingAttempt.Status.SUCCESS,
            server_response="Успешно",
        )

    def test_anonymous_user_cannot_view_statistics(self):
        """Гость не получает доступ к статистике."""

        response = self.client.get(reverse("mailing_statistics"))

        self.assertEqual(response.status_code, 302)

    def test_statistics_counts_are_correct(self):
        """Счётчики учитывают только собственные попытки."""

        self.client.force_login(self.user)

        response = self.client.get(reverse("mailing_statistics"))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["total_mailings"],
            1,
        )

        self.assertEqual(
            response.context["total_attempts"],
            3,
        )

        self.assertEqual(
            response.context["successful_attempts"],
            2,
        )

        self.assertEqual(
            response.context["failed_attempts"],
            1,
        )

        self.assertEqual(
            response.context["sent_messages"],
            2,
        )

    def test_statistics_do_not_include_foreign_mailings(self):
        """Пользователь не видит чужую статистику."""

        self.client.force_login(self.user)

        response = self.client.get(reverse("mailing_statistics"))

        self.assertNotContains(
            response,
            "Чужая рассылка",
        )

        mailing_stats = list(response.context["mailing_stats"])

        self.assertEqual(len(mailing_stats), 1)

        self.assertEqual(
            mailing_stats[0].pk,
            self.mailing.pk,
        )

        self.assertEqual(
            mailing_stats[0].successful_attempts,
            2,
        )

        self.assertEqual(
            mailing_stats[0].failed_attempts,
            1,
        )

    def test_user_without_mailings_sees_zero_statistics(self):
        """Новый пользователь получает нулевые показатели."""

        self.client.force_login(self.empty_user)

        response = self.client.get(reverse("mailing_statistics"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["total_mailings"],
            0,
        )
        self.assertEqual(
            response.context["total_attempts"],
            0,
        )
        self.assertEqual(
            response.context["successful_attempts"],
            0,
        )
        self.assertEqual(
            response.context["failed_attempts"],
            0,
        )
