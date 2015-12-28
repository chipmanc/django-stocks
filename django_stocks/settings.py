from django.conf import settings

DATA_DIR = settings.django_sec_DATA_DIR = getattr(
    settings,
    'django_sec_DATA_DIR',
    '/tmp/django_sec')