from typing import ClassVar

from django import forms

from mailings.models import Mailing, Message, Recipient


class RecipientForm(forms.ModelForm):
    """Форма добавления и редактирования получателя."""

    class Meta:
        model = Recipient
        fields = ("email", "full_name", "comment")

        widgets: ClassVar[dict[str, forms.Widget]] = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "example@email.com",
                }
            ),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class MessageForm(forms.ModelForm):
    """Форма создания и редактирования сообщения."""

    class Meta:
        model = Message
        fields = ("subject", "body")

        widgets: ClassVar[dict[str, forms.Widget]] = {
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Введите тему письма",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "Введите текст письма",
                }
            ),
        }


class MailingForm(forms.ModelForm):
    """Форма создания и редактирования рассылки."""

    class Meta:
        model = Mailing

        fields = (
            "start_time",
            "end_time",
            "message",
            "recipients",
        )

        widgets: ClassVar[dict[str, forms.Widget]] = {
            "start_time": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "end_time": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "message": forms.Select(attrs={"class": "form-select"}),
            "recipients": forms.SelectMultiple(
                attrs={
                    "class": "form-select",
                    "size": 6,
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is None or not user.is_authenticated:
            self.fields["message"].queryset = Message.objects.none()
            self.fields["recipients"].queryset = Recipient.objects.none()
            return

        self.fields["message"].queryset = Message.objects.filter(owner=user)

        self.fields["recipients"].queryset = Recipient.objects.filter(owner=user)
