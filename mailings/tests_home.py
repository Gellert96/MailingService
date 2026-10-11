from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from mailings.models import Mailing, Message, Recipient

User = get_user_model()


class HomeStatisticsTests(TestCase):
    """Тесты общей статистики главной страницы."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="home-user@example.com",
            password="TestPassword123!",
        )

        cls.other_user = User.objects.create_user(
            email="home-other@example.com",
            password="TestPassword123!",
        )

        Recipient.objects.create(
            owner=cls.user,
            email="home-recipient1@example.com",
            full_name="Первый получатель",
        )

        Recipient.objects.create(
            owner=cls.other_user,
            email="home-recipient2@example.com",
            full_name="Второй получатель",
        )

        message = Message.objects.create(
            owner=cls.user,
            subject="Первое письмо",
            body="Текст первого письма",
        )

        other_message = Message.objects.create(
            owner=cls.other_user,
            subject="Второе письмо",
            body="Текст второго письма",
        )

        now = timezone.now()

        # Активная рассылка
        cls.active_mailing = Mailing.objects.create(
            owner=cls.other_user,
            message=other_message,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            status=Mailing.Status.CREATED,
        )

        # Будущая рассылка
        cls.future_mailing = Mailing.objects.create(
            owner=cls.user,
            message=message,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=Mailing.Status.RUNNING,
        )

        # Завершённая рассылка
        cls.completed_mailing = Mailing.objects.create(
            owner=cls.other_user,
            message=other_message,
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=2),
            status=Mailing.Status.RUNNING,
        )

        # Отключённая рассылка
        cls.disabled_mailing = Mailing.objects.create(
            owner=cls.other_user,
            message=other_message,
            start_time=now - timedelta(minutes=30),
            end_time=now + timedelta(minutes=30),
            is_enabled=False,
        )

    def test_guest_sees_global_statistics(self):
        """Гость видит общую статистику системы."""

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_mailings"], 4)
        self.assertEqual(response.context["active_mailings"], 1)
        self.assertEqual(response.context["total_recipients"], 2)

    def test_user_sees_global_statistics(self):
        """Пользователь видит все рассылки, а не только свои."""

        self.client.force_login(self.user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_mailings"], 4)
        self.assertEqual(response.context["active_mailings"], 1)
        self.assertEqual(response.context["total_recipients"], 2)

    def test_home_updates_mailing_statuses(self):
        """Главная обновляет временные статусы рассылок."""

        self.client.get(reverse("home"))

        self.active_mailing.refresh_from_db()
        self.future_mailing.refresh_from_db()
        self.completed_mailing.refresh_from_db()

        self.assertEqual(
            self.active_mailing.status,
            Mailing.Status.RUNNING,
        )

        self.assertEqual(
            self.future_mailing.status,
            Mailing.Status.CREATED,
        )

        self.assertEqual(
            self.completed_mailing.status,
            Mailing.Status.COMPLETED,
        )

    def test_disabled_mailing_is_not_active(self):
        """Отключённые рассылки не учитываются как активные."""

        self.active_mailing.is_enabled = False
        self.active_mailing.save(update_fields=["is_enabled"])

        response = self.client.get(reverse("home"))

        self.assertEqual(
            response.context["active_mailings"],
            0,
        )
