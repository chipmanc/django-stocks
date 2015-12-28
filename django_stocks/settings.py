from django.conf import settings

DATA_DIR = settings.django_stocks_DATA_DIR = getattr(
    settings,
    'django_stocks_DATA_DIR',
    '/tmp/django_stocks')