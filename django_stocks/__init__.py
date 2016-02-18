from __future__ import absolute_import
from .celery import app as celery_app

VERSION = (0, 4, 3)
__version__ = '.'.join(map(str, VERSION))
