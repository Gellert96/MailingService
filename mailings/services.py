from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils import timezone

from mailings.models import MailingAttempt
from mailings.statistics_cache import invalidate_user_statistics


def send_mailing(mailing):
    """Отправляет рассылку и сохраняет историю попыток."""

    now = timezone.now()

    mailing.update_status()

    # Проверяем, что менеджер не отключил рассылку
    if not mailing.is_enabled:
        raise ValidationError("Эта рассылка отключена менеджером. Отправка запрещена.")

    # Проверяем разрешённое время отправки
    if not mailing.start_time <= now <= mailing.end_time:
        raise ValidationError(
            "Рассылку можно отправить только между датой начала и датой окончания."
        )

    # Сообщение должно принадлежать владельцу рассылки
    if mailing.message.owner_id != mailing.owner_id:
        raise ValidationError("Невозможно отправить чужое сообщение.")

    recipients = list(mailing.recipients.all())

    if not recipients:
        raise ValidationError("Невозможно отправить рассылку без получателей.")

    # Все получатели должны принадлежать владельцу рассылки
    if any(recipient.owner_id != mailing.owner_id for recipient in recipients):
        raise ValidationError("Рассылка содержит получателей другого пользователя.")

    attempts = []
    successful_count = 0
    failed_count = 0

    for recipient in recipients:
        try:
            result = send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
            )

            if result == 1:
                status = MailingAttempt.Status.SUCCESS
                response = "Письмо успешно обработано почтовым backend."
                successful_count += 1
            else:
                status = MailingAttempt.Status.FAILED
                response = "Почтовый backend не отправил письмо."
                failed_count += 1

        except Exception as error:  # noqa: BLE001
            status = MailingAttempt.Status.FAILED
            response = f"{type(error).__name__}: {error}"
            failed_count += 1

        attempts.append(
            MailingAttempt(
                mailing=mailing,
                status=status,
                server_response=response,
            )
        )

    # Сохраняем историю попыток
    MailingAttempt.objects.bulk_create(attempts)

    # Очищаем устаревшую статистику
    invalidate_user_statistics(mailing.owner_id)

    return {
        "successful": successful_count,
        "failed": failed_count,
    }
