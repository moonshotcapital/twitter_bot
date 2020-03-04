"""
Django settings for bot project.

Generated by 'django-admin startproject' using Django 2.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import dj_database_url

from celery.schedules import crontab

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '2etpf#=w%qcbdeulchat$+z+*e=up8!iyg%+ynk3hhf^5qux6)')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('DJANGO_DEBUG', True))

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]


INSTALLED_APPS += [
    'django_celery_results',
    'django_celery_beat',
    'django_extensions'
]

INSTALLED_APPS += [
    'twitterbot.apps.TwitterbotConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'twitterdb'),
        'USER': os.environ.get('DATABASE_USER', 'twitterbotadmin'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', 'twitterbotadmin2018'),
        'HOST': os.environ.get('DATABASE_HOST', ''),
        'PORT': os.environ.get('DATABASE_PORT', 5432),
    }
}

db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(db_from_env)

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATIC_URL = '/static/'


# Celery settings

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    'twitter_follower_bot_task': {
        'task': 'twitterbot.tasks.follow_people',
        'schedule': crontab(hour='7,13,19', minute=30),
    },
    'update_followers_list_task': {
        'task': 'twitterbot.tasks.update_followers_list_task',
        'schedule': crontab(hour=21, minute=30),
    },
    'retweet_task': {
        'task': 'twitterbot.tasks.retweet_task',
        'schedule': crontab(hour='10,12,15', minute=0),
    },
    'unfollow_users_task': {
        'task': 'twitterbot.tasks.unfollow_users_task',
        'schedule': crontab(hour='7,13,19', minute=0),
    },
}


# Tweepy authentication

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')

SLACK_API_TOKEN = os.environ.get('SLACK_API_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL')

TELEGRAM_NOTIFICATIONS_TOKEN = os.environ.get('TELEGRAM_NOTIFICATIONS_TOKEN')

# followers_limit -> this values is used for limit of number of followers and
# unfollowers. random.randrange(limit, limit+10)
TWITTER_ACCOUNT_SETTINGS = {
    'a_soldatenko': {
        'unfollow': ['utils.twitterbot.make_unfollow_for_current_account'],
        'follow': ['utils.twitterbot.make_follow_for_current_account'],
        'followers_limit': 10
    },
    'goformoonshot': {
        'unfollow': ['utils.twitterbot.make_unfollow_for_current_account'],
        'follow': ['utils.twitterbot.make_follow_for_current_account',
                   'utils.twitterbot.follow_all_own_followers'],
        'followers_limit': 40,
        'retweet': ['utils.twitterbot.retweet_verified_users_with_tag']
    },
    'sake_arts': {
        'unfollow': ['utils.twitterbot.make_unfollow_for_current_account'],
        'follow': ['utils.twitterbot.make_follow_for_current_account'],
        'followers_limit': 40,
        'retweet': ['utils.twitterbot.retweet_verified_users'],
        'csv_statistic': True
    },
}
