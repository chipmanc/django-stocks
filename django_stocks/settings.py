from django.conf import settings

DATA_DIR = settings.django_stocks_DATA_DIR = getattr(
    settings,
    'django_stocks_DATA_DIR',
    '/tmp/django_stocks')

#  For a complete list of Celery options see
#  http://docs.celeryproject.org/en/latest/configuration.html
settings.BROKER_URL = 'amqp://127.0.0.1'
settings.CELERY_ACCEPT_CONTENT = ['json']
settings.CELERY_TASK_SERIALIZER = 'json'
settings.CELERY_RESULT_SERIALIZER = 'json'
