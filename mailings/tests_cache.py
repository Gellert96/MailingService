from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from mailings.models import Mailing, MailingAttempt, Message
from mailings.statistics_cache import get_cached_statistics

User = get_user_model()


class StatisticsCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="cache@example.com",
            password="TestPassword123!",
        )

        cls.other_user = User.objects.create_user(
            email="other-cache@example.com",
            password="TestPassword123!",
        )

        message = Message.objects.create(
            owner=cls.user,
            subject="Тест кеширования",
            body="Проверяем статистику.",
        )

        now = timezone.now()

        cls.mailing = Mailing.objects.create(
            owner=cls.user,
            message=message,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )

    def setUp(self):
        cache.clear()

    def test_statistics_are_cached(self):
        """Повторное чтение не обращается к базе данных."""

        with self.assertNumQueries(1):
            first_result = get_cached_statistics(self.user.pk)

        with self.assertNumQueries(0):
            second_result = get_cached_statistics(self.user.pk)

        self.assertEqual(first_result, second_result)

    def test_new_attempt_invalidates_cache(self):
        """Новая попытка обновляет закешированные показатели."""

        first_result = get_cached_statistics(self.user.pk)
        self.assertEqual(first_result["successful_attempts"], 0)

        MailingAttempt.objects.create(
            mailing=self.mailing,
            status=MailingAttempt.Status.SUCCESS,
            server_response="OK",
        )

        updated_result = get_cached_statistics(self.user.pk)

        self.assertEqual(updated_result["successful_attempts"], 1)

    def test_deleted_attempt_invalidates_cache(self):
        """Удаление попытки обновляет статистику."""

        attempt = MailingAttempt.objects.create(
            mailing=self.mailing,
            status=MailingAttempt.Status.FAILED,
            server_response="SMTP error",
        )

        result = get_cached_statistics(self.user.pk)
        self.assertEqual(result["failed_attempts"], 1)

        attempt.delete()

        updated_result = get_cached_statistics(self.user.pk)
        self.assertEqual(updated_result["failed_attempts"], 0)

    def test_users_have_separate_cache(self):
        """Статистика одного пользователя не попадает к другому."""

        MailingAttempt.objects.create(
            mailing=self.mailing,
            status=MailingAttempt.Status.SUCCESS,
            server_response="OK",
        )

        own_statistics = get_cached_statistics(self.user.pk)
        other_statistics = get_cached_statistics(self.other_user.pk)

        self.assertEqual(own_statistics["successful_attempts"], 1)
        self.assertEqual(other_statistics["successful_attempts"], 0)
