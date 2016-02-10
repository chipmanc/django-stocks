import collections
from datetime import datetime
from optparse import make_option
import random
import re
from StringIO import StringIO
import sys
import time
import traceback

from django.core.management.base import BaseCommand
from django.db import transaction, connection, DatabaseError

from django_stocks import models
from django_stocks.tasks import import_attrs


def is_power_of_two(x):
    return (x & (x - 1)) == 0


class Command(BaseCommand):
    help = "Shows data from filings."
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--cik',
                    type=int,
                    default=None),
        make_option('--forms',
                    default='10-K,10-Q'),
        make_option('--start-year',
                    default=datetime.now().year,
                    type=int),
        make_option('--end-year',
                    default=datetime.now().year,
                    type=int),
        make_option('--quarter',
                    default=None),
        make_option('--dryrun',
                    action='store_true',
                    default=False),
        make_option('--force',
                    action='store_true',
                    default=False),
        make_option('--verbose',
                    action='store_true',
                    default=False),
    )

    def print_progress(self, message,
                       current_count=0, total_count=0,
                       sub_current=0, sub_total=0):
        bar_length = 10
        if total_count:
            percent = current_count / float(total_count)
            bar = ('=' * int(percent * bar_length)).ljust(bar_length)
            percent = int(percent * 100)
        else:
            sys.stdout.write(message)
            sys.stdout.flush()
            return

        if sub_current and sub_total:
            sub_status = '(subtask %s of %s) ' % (sub_current, sub_total)
        else:
            sub_status = ''

        sys.stdout.write("[%s] %s of %s %s%s%%  %s\n"
                         % (bar, current_count, total_count, sub_status, percent, message))
        sys.stdout.flush()

    def handle(self, **options):
        options['forms'] = options['forms'].split(',')
        transaction.enter_transaction_management()
        transaction.managed(True)

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
            if options['cik']:
                q = q.filter(company__cik=options['cik'])
            if not options['force']:
                q = q.filter(company__load=True)
            if not q.count():
                print>>sys.stderr, ('Warning: the company you specified with cik %s is '
                                    'either not marked for loading or does not exist.') % (options['cik'])

            total_count = q.count()
            current_count = 0
            commit_freq = 300
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
        finally:
            if options['dryrun']:
                print 'This is a dryrun, so no changes were committed.'
                transaction.rollback()
            else:
                transaction.commit()
            transaction.leave_transaction_management()
            connection.close()
