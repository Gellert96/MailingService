"""
Настройки Django для проекта MailingService.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# --------------------------------------------------
# Базовые настройки проекта
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Загружаем переменные окружения из .env
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY не найден. Добавьте его в файл .env.")

DEBUG = os.getenv("DEBUG", "True").lower() in {
    "true",
    "1",
    "yes",
    "on",
}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]


# --------------------------------------------------
# Установленные приложения
# --------------------------------------------------

INSTALLED_APPS = [
    # WhiteNoise для обслуживания статики при разработке
    "whitenoise.runserver_nostatic",
    # Стандартные приложения Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Приложения проекта
    "accounts",
    "mailings.apps.MailingsConfig",
]


# --------------------------------------------------
# Middleware
# --------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# --------------------------------------------------
# URL и шаблоны
# --------------------------------------------------

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "mailings.context_processors.manager_access",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# --------------------------------------------------
# База данных PostgreSQL
# --------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv(
            "DB_NAME",
            os.getenv("POSTGRES_DB", "mailing_service"),
        ),
        "USER": os.getenv(
            "DB_USER",
            os.getenv("POSTGRES_USER", "postgres"),
        ),
        "PASSWORD": os.getenv(
            "DB_PASSWORD",
            os.getenv("POSTGRES_PASSWORD", ""),
        ),
        "HOST": os.getenv(
            "DB_HOST",
            os.getenv("POSTGRES_HOST", "localhost"),
        ),
        "PORT": os.getenv(
            "DB_PORT",
            os.getenv("POSTGRES_PORT", "5432"),
        ),
    },
}


# --------------------------------------------------
# Пользователи и аутентификация
# --------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "home"

LOGOUT_REDIRECT_URL = "home"


# --------------------------------------------------
# Проверка паролей
# --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator"),
    },
]


# --------------------------------------------------
# Язык, время и локализация
# --------------------------------------------------

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Asia/Yerevan"

USE_I18N = True

USE_TZ = True


# --------------------------------------------------
# Электронная почта
# --------------------------------------------------

# Django 6.1: используется MAILERS.
# При локальной разработке письма выводятся в терминал.

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "MailingService <noreply@example.com>",
)


# --------------------------------------------------
# Статические файлы и клиентское кеширование
# --------------------------------------------------

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": ("whitenoise.storage.CompressedManifestStaticFilesStorage"),
    },
}

# В режиме разработки обычные статические файлы
# кешируются на 60 секунд.
# В рабочем режиме — на 3600 секунд.
# Хешированные файлы кешируются дольше.

WHITENOISE_MAX_AGE = 60 if DEBUG else 3600


# --------------------------------------------------
# Серверное кеширование
# --------------------------------------------------

# Используем встроенное кеширование Django.
# Docker и Redis не требуются.

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mailingservice-cache",
        "TIMEOUT": 300,
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    },
}


# --------------------------------------------------
# Настройки моделей
# --------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
