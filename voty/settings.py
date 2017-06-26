"""
Django settings for voty project.

Generated by 'django-admin startproject' using Django 1.10.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET', '&v--b40hjwtfre(o^(4=-s!g7!x&za1u_=v#140ex+_%iek(c#');


DEBUG = not os.environ.get('VIRTUAL_HOST', False)

ALLOWED_HOSTS = os.environ.get('VIRTUAL_HOST', 'localhost,screwdriver.fritz.box').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd party
    'account',
    'avatar',
    'mathfilters',
    'mailer',
    'pinax.notifications',
    'notifications',
    'bootstrapform',
    'fullurl',
    'django_ajax',

    # must be before admin ...
    'dal',
    'dal_select2',
    'django.contrib.admin',

    # locally
    'voty.initadmin',
    'voty.initproc'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'voty.initproc.guard.add_guard',
    'voty.initadmin.notify_backend.mark_as_read',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "account.middleware.LocaleMiddleware",
    "account.middleware.TimezoneMiddleware"
]


PINAX_NOTIFICATIONS_BACKENDS = [
    ("site", "voty.initadmin.notify_backend.SiteBackend"),
    ("email", "pinax.notifications.backends.email.EmailBackend"),
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}


AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

)

ROOT_URLCONF = 'voty.urls'
LOGIN_URL = "/account/login/"
LOGIN_REDIRECT_URL = "/"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'account.context_processors.account',
            ],
        },
    },
]

WSGI_APPLICATION = 'voty.wsgi.application'

SITE_ID = 1

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(default='sqlite://./db.sqlite3')
}


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

NOTIFICATIONS_USE_JSONFIELD=True

ACCOUNT_OPEN_SIGNUP = False
AVATAR_GRAVATAR_DEFAULT = 'retro'


DEFAULT_FROM_EMAIL = 'keine-antwort@bewegung.jetzt'
EMAIL_BACKEND = "mailer.backend.DbBackend"

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

elif os.environ.get('SPARKPOST_API_KEY', None):
    SPARKPOST_API_KEY = os.environ.get('SPARKPOST_API_KEY')
    MAILER_EMAIL_BACKEND = 'sparkpost.django.email_backend.SparkPostEmailBackend'
    SPARKPOST_OPTIONS = {
        'track_opens': False,
        'track_clicks': False,
        'transactional': True,
    }


else:
    MAILER_EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_USE_TLS = True
    EMAIL_HOST = os.environ.get("SMTP_SERVER", "smtp.mailgun.org")
    EMAIL_HOST_USER = os.environ.get("SMTP_USERNAME", 'mymail@gmail.com')
    EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", 'password')
    EMAIL_PORT = int(os.environ.get("SMTP_PORT", 587))


from django.contrib import messages

MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

## What we allow in the editor

MARKDOWN_FILTER_WHITELIST_TAGS = ['a', 'p', 'b', 'em', 'strong', 'i', 'code', 'pre', 'blockquote', 'ul', 'ol', 'li']


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join( BASE_DIR, 'static'),
)


STATIC_ROOT = os.path.join( BASE_DIR, 'public', 'static')
MEDIA_ROOT = os.path.join( BASE_DIR, 'public', 'media')