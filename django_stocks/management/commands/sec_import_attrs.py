import urllib
import os
import re
import sys
from zipfile import ZipFile
import time
from datetime import date, datetime, timedelta
from optparse import make_option
from StringIO import StringIO
import traceback
import random
import collections

from django.core.management.base import NoArgsCommand, BaseCommand
from django.db import transaction, connection, IntegrityError, DatabaseError
from django.conf import settings
from django.utils import timezone

from django_stocks import models
from django_stocks.models import DATA_DIR, c


def is_power_of_two(x):
    return (x & (x - 1)) == 0

def parse_stripe(stripe):
    stripe_num = None
    stripe_mod = None
    if stripe:
        assert isinstance(stripe, basestring) and len(stripe) == 2
        stripe_num, stripe_mod = stripe
        stripe_num = int(stripe_num)
        stripe_mod = int(stripe_mod)
        assert stripe_num < stripe_mod
    return stripe_num, stripe_mod

class Command(BaseCommand):
    help = "Shows data from filings."
    args = ''
    option_list = BaseCommand.option_list + (
        make_option('--cik',
                    default=None),
        make_option('--forms',
                    default='10-K,10-Q'),
        make_option('--start-year',
                    default=datetime.now().year),
        make_option('--end-year',
                    default=datetime.now().year),
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
        self.dryrun = options['dryrun']
        self.force = options['force']
        self.verbose = options['verbose']
        self.forms = (options['forms'] or '').strip().split(',')
        self.start_year = int(options['start_year'])
        self.end_year = int(options['end_year'])
        self.cik = (int(options['cik']) or None)

        self.stripe_counts = {} # {stripe:{current,total}
        self.last_progress_refresh = None
        self.start_times = {} # {key:start_time}
        self.progress = collections.OrderedDict()
        kwargs = options.copy()
        self.start_times[None] = time.time()
        self.import_attributes(**kwargs)

    def print_progress(self):
        if (self.last_progress_refresh and 
            (datetime.now()-self.last_progress_refresh).seconds < 0.5):
            return
        bar_length = 10
        for (stripe, (current, total, sub_current,
                      sub_total, eta, message)) in sorted(self.progress.items()):
            sub_status = ''
            if total:
                if not eta:
                    start_time = self.start_times[stripe]
                    current_seconds = time.time() - start_time
                    total_seconds = float(total)/current*current_seconds
                    remaining_seconds = int(total_seconds - current_seconds)
                    eta = timezone.now() + timedelta(seconds=remaining_seconds)

                self.stripe_counts[stripe] = (current, total)
                percent = current/float(total)
                bar = ('=' * int(percent * bar_length)).ljust(bar_length)
                percent = int(percent * 100)
            else:
                eta = eta or '?'
                percent = 0
                bar = ('=' * int(percent * bar_length)).ljust(bar_length)
                percent = '?'
                total = '?'
            if sub_current and sub_total:
                sub_status = '(subtask %s of %s) ' % (sub_current, sub_total)
            sys.stdout.write(
                ("%s [%s] %s of %s %s%s%% eta=%s: %s\n") \
                    % (stripe, bar, current, total, sub_status, percent, eta, message))
        sys.stdout.flush()
        self.last_progress_refresh = datetime.now()

        overall_current_count = 0
        overall_total_count = 0
        for stripe, (current, total) in self.stripe_counts.iteritems():
            overall_current_count += current
            overall_total_count += total


    def import_attributes(self, **kwargs):
        transaction.enter_transaction_management()
        transaction.managed(True)

        stripe = kwargs.get('stripe')
        reraise = kwargs.get('reraise')

        current_count = 0
        total_count = 0
        fatal_errors = False
        fatal_error = None
        estimated_completion_datetime = None
        sub_current = 0
        sub_total = 0

        def print_status(message, count=None, total=None):
            current_count = count or 0
            total_count = total or 0
            self.progress[stripe] = (
                current_count,
                total_count,
                sub_current,
                sub_total,
                estimated_completion_datetime,
                message)
            self.print_progress()

        stripe_num, stripe_mod = parse_stripe(stripe)
        if stripe:
            print_status('Striping with number %i and modulus %i.' \
                % (stripe_num, stripe_mod))

        try:
            # Get a file from the index.
            # It may or may not be present on our hard disk.
            # If it's not, it will be downloaded
            # the first time we try to access it, or you can call
            # .download() explicitly.
            q = models.Index.objects.filter(
                year__gte=self.start_year,
                year__lte=self.end_year)
            if not self.force:
                q = q.filter(
                    attributes_loaded__exact=0,  # False,
                    valid__exact=1,  # True,
                )
            if self.forms:
                q = q.filter(form__in=self.forms)

            q2 = q
            if self.cik:
                q = q.filter(company__cik=self.cik, company__load=True)
                q2 = q2.filter(company__cik=self.cik)
                if not q.count() and q2.count():
                    print>>sys.stderr, 'Warning: the company you specified with cik %s is not marked for loading.' % (self.cik,)

            if stripe is not None:
                q = q.extra(where=['(("django_stocks_index"."id" %%%% %i) = %i)' % (stripe_mod, stripe_num)])

            total_count = total = q.count()


            print_status('%i total rows.' % (total,))
            i = 0
            commit_freq = 100
            print_status('%i indexes found for forms %s.' % (total, ', '.join(self.forms)), count=0, total=total)
            for ifile in q.iterator():
                i += 1
                current_count = i

                msg = 'Processing index %s.' % (ifile.filename,)
                print_status(msg, count=i, total=total)

                if not i % commit_freq:
                    sys.stdout.flush()
                    if not self.dryrun:
                        transaction.commit()

                ifile.download(verbose=self.verbose)

                # Initialize XBRL parser and populate an attribute called fields with
                # a dict of 50 common terms.
                x = None
                error = None
                try:
                    x = ifile.xbrl()
                except Exception, e:
                    ferr = StringIO()
                    traceback.print_exc(file=ferr)
                    error = ferr.getvalue()

                if x is None:
                    if error is None:
                        error = 'No XBRL found.'
                    models.Index.objects.filter(id=ifile.id)\
                        .update(valid=False, error=error)
                    continue

                maxretries = 10
                retry = 0
                while 1:
                    try:

                        company = ifile.company
                        max_text_len = 0
                        unique_attrs = set()
                        bulk_objects = []
                        prior_keys = set()
                        j = sub_total = 0
                        for node, sub_total in x.iter_namespace():
                            j += 1
                            sub_current = j
                            if not j % commit_freq:
                                print_status(msg, count=i, total=total)
                                if not self.dryrun:
                                    transaction.commit()

                            matches = re.findall('^\{([^\}]+)\}(.*)$', node.tag)
                            if matches:
                                ns, attr_name = matches[0]
                            else:
                                ns = None
                                attr_name = node
                            decimals = node.attrib.get('decimals', None)
                            if decimals is None:
                                continue
                            if decimals.upper() == 'INF':
                                decimals = 6
                            decimals = int(decimals)
                            max_text_len = max(max_text_len, len((node.text or '').strip()))
                            context_id = node.attrib['contextRef']
                            start_date = x.get_context_start_date(context_id)
                            if not start_date:
                                continue
                            end_date = x.get_context_end_date(context_id)
                            if not end_date:
                                continue
                            namespace, _ = models.Namespace.objects.get_or_create(name=ns.strip())
                            attribute, _ = models.Attribute.objects.get_or_create(
                                namespace=namespace,
                                name=attr_name,
                                defaults=dict(load=True),
                            )
                            if not attribute.load:
                                continue
                            unit, _ = models.Unit.objects.get_or_create(name=node.attrib['unitRef'].strip())
                            value = (node.text or '').strip()
                            if not value:
                                continue
                            assert len(value.split('.')[0]) <= c.MAX_QUANTIZE, \
                                'Value too large, must be less than %i digits: %i %s' \
                                    % (c.MAX_QUANTIZE, len(value), repr(value))

                            models.Attribute.objects.filter(id=attribute.id).update(total_values_fresh=False)

                            if models.AttributeValue.objects.filter(company=company, attribute=attribute, start_date=start_date).exists():
                                continue

                            # Some attributes are listed multiple times in differently
                            # named contexts even though the value and date ranges are
                            # identical.
                            key = (company, attribute, start_date)
                            if key in prior_keys:
                                continue
                            prior_keys.add(key)

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
                                prior_keys.clear()

                        if not self.dryrun:
                            transaction.commit()
                        print_status('Importing attributes.', count=i, total=total)

                        if bulk_objects:
                            models.AttributeValue.objects.bulk_create(bulk_objects)
                            bulk_objects = []

                        ticker = ifile.ticker()
                        models.Index.objects.filter(id=ifile.id).update(attributes_loaded=True, _ticker=ticker)

                        models.Attribute.do_update()

                        models.Unit.do_update()

                        if not self.dryrun:
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
            print_status('Fatal error: %s' % (error,))
        finally:
            if self.dryrun:
                print 'This is a dryrun, so no changes were committed.'
                transaction.rollback()
            else:
                transaction.commit()
            transaction.leave_transaction_management()
            connection.close()

