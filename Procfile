web: gunicorn bot.wsgi --log-file -
beat: celery -A bot worker -B
release: python manage.py migrate