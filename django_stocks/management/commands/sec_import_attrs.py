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

    def handle(self, **options):

        kwargs = options.copy()
        self.import_attributes(**kwargs)

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

    def import_attributes(self, **kwargs):
        kwargs['forms'] = kwargs['forms'].split(',')
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
                year__gte=kwargs['start_year'],
                year__lte=kwargs['end_year'])
            if not kwargs['force']:
                q = q.filter(
                    attributes_loaded__exact=0,
                    valid__exact=1,)
            if kwargs['forms']:
                q = q.filter(form__in=kwargs['forms'])
            if kwargs['cik']:
                q = q.filter(company__cik=kwargs['cik'])
            if not kwargs['force']:
                q = q.filter(company__load=True)
            if not q.count():
                print>>sys.stderr, ('Warning: the company you specified with cik %s is '
                                    'either not marked for loading or does not exist.') % (kwargs['cik'])

            total_count = q.count()
            current_count = 0
            commit_freq = 300
            for ifile in q.iterator():
                current_count += 1

                msg = 'Processing index %s.' % (ifile.filename,)
                self.print_progress(msg, current_count, total_count)

                ifile.download(verbose=kwargs['verbose'])

                x = None
                error = None
                try:
                    x = ifile.xbrl()
                except Exception, e:
                    ferr = StringIO()
                    traceback.print_exc(file=ferr)
                    error = ferr.getvalue()
                    print error
                    models.Index.objects.filter(id=ifile.id).update(valid=False, error=error)

                if x is None:
                    error = 'No XBRL found.'
                    models.Index.objects.filter(id=ifile.id).update(valid=False, error=error)
                    continue

                maxretries = 10
                retry = 0
                while 1:
                    try:
                        company = ifile.company
                        bulk_objects = []
                        sub_current = 0
                        for node, sub_total in x.iter_namespace():
                            sub_current += 1
                            if not sub_current % commit_freq:
                                self.print_progress(msg,
                                                    current_count,
                                                    total_count,
                                                    sub_current,
                                                    sub_total)

                            matches = re.findall('^\{([^\}]+)\}(.*)$', node.tag)
                            if matches:
                                ns, attr_name = matches[0]
                            else:
                                ns = None
                                attr_name = node

                            decimals = node.attrib.get('decimals', None)
                            if decimals is None:
                                continue
                            elif decimals.upper() == 'INF':
                                decimals = 6
                            else:
                                decimals = int(decimals)

                            context_id = node.attrib['contextRef']
                            start_date = x.get_context_start_date(context_id)
                            if not start_date:
                                continue
                            end_date = x.get_context_end_date(context_id)
                            if not end_date:
                                continue
                            namespace, _ = models.Namespace.objects.get_or_create(name=ns.strip())
                            attribute, _ = models.Attribute.objects.get_or_create(namespace=namespace,
                                                                                  name=attr_name,
                                                                                  defaults=dict(load=True))
                            if not attribute.load:
                                continue
                            unit, _ = models.Unit.objects.get_or_create(name=node.attrib['unitRef'].strip())
                            value = (node.text or '').strip()
                            if not value:
                                continue
                            assert len(value.split('.')[0]) <= models.c.MAX_QUANTIZE, \
                                'Value too large, must be less than %i digits: %i %s' \
                                % (models.c.MAX_QUANTIZE, len(value), repr(value))

                            models.Attribute.objects.filter(id=attribute.id).update(total_values_fresh=False)

                            if models.AttributeValue.objects.filter(company=company, attribute=attribute, start_date=start_date).exists():
                                continue

                            bulk_objects.append(models.AttributeValue(
                                company=company,
                                attribute=attribute,
                                start_date=start_date,
                                end_date=end_date,
                                value=value,
                                unit=unit,
                                filing_date=ifile.date,
                            ))

                            if not len(bulk_objects) % commit_freq:
                                models.AttributeValue.objects.bulk_create(bulk_objects)
                                bulk_objects = []

                        if not kwargs['dryrun']:
                            transaction.commit()
                        self.print_progress('Importing attributes.', current_count, total_count)

                        if bulk_objects:
                            models.AttributeValue.objects.bulk_create(bulk_objects)
                            bulk_objects = []

                        ticker = ifile.ticker()
                        models.Index.objects.filter(id=ifile.id).update(attributes_loaded=True, _ticker=ticker)
                        models.Attribute.do_update()
                        models.Unit.do_update()

                        if not kwargs['dryrun']:
                            transaction.commit()

                        break

                    except DatabaseError, e:
                        if retry+1 == maxretries:
                            raise
                        print e, 'retry', retry
                        connection.close()
                        time.sleep(random.random()*5)

        except Exception, e:
            ferr = StringIO()
            traceback.print_exc(file=ferr)
            error = ferr.getvalue()
            self.print_progress('Fatal error: %s' % (error,))
        finally:
            if kwargs['dryrun']:
                print 'This is a dryrun, so no changes were committed.'
                transaction.rollback()
            else:
                transaction.commit()
            transaction.leave_transaction_management()
            connection.close()
