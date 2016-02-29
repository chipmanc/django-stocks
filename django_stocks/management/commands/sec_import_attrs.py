import collections
from datetime import datetime
import random
import re
from StringIO import StringIO
import sys
import time
import traceback

from django.core.management.base import BaseCommand
from django.db import DatabaseError

from django_stocks import models
from django_stocks.tasks import import_attrs


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--cik',
                            type=int,
                            default=None)
        parser.add_argument('--forms',
                            default='10-K,10-Q')
        parser.add_argument('--start-year',
                            default=datetime.now().year,
                            type=int)
        parser.add_argument('--end-year',
                            default=datetime.now().year,
                            type=int)
        parser.add_argument('--quarter',
                            default=None)
        parser.add_argument('--dryrun',
                            action='store_true',
                            default=False)
        parser.add_argument('--force',
                            action='store_true',
                            default=False)
        parser.add_argument('--verbose',
                            action='store_true',
                            default=False)

    def handle(self, *args, **options):
        options['forms'] = options['forms'].split(',')

        sub_current = 0
        sub_total = 0

        try:
            # Get a file from the index.
            # It may or may not be present on our hard disk.
            # If it's not, it will be downloaded
            # the first time we try to access it, or you can call
            # .download() explicitly.
            q = models.Index.objects.filter(
                year__gte=options['start_year'],
                year__lte=options['end_year'])
            if not options['force']:
                q = q.filter(
                    attributes_loaded__exact=0,
                    valid__exact=1,)
            if options['forms']:
                q = q.filter(form__in=options['forms'])
            if options['quarter']:
                q = q.filter(quarter__in=options['quarter'])
            if options['cik']:
                q = q.filter(company__cik=options['cik'])
            if not options['force']:
                q = q.filter(company__load=True)
            if not q.count():
                print>>sys.stderr, ('Warning: the company you specified with cik %s is '
                                    'either not marked for loading or does not exist.') % (options['cik'])

            kwargs = options.copy()
            for ifile in q.iterator():
                kwargs['filename'] = ifile.filename
                kwargs['total_count'] = total_count
                import_attrs.delay(**kwargs)

        except Exception, e:
            ferr = StringIO()
            traceback.print_exc(file=ferr)
            error = ferr.getvalue()
            self.print_progress('Fatal error: %s' % (error,))
