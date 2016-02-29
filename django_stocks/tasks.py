from __future__ import absolute_import

from datetime import date, datetime
from functools import partial
import os
import re
from StringIO import StringIO
import sys
import time
import traceback
import urllib
from zipfile import ZipFile

from celery import shared_task
from django.db import DatabaseError
from django.utils import timezone
from django.utils.encoding import force_text

from django_stocks.constants import MAX_QUANTIZE
from django_stocks.models import Attribute, AttributeValue, Company, Index, IndexFile, Namespace, Unit, DATA_DIR


def print_progress(message,
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


@shared_task(max_retries=5, default_retry_delay=20)
def get_filing_list(year, quarter, reprocess=False):
    """
    Gets the list of filings and download locations for the given
    year and quarter.
    """
    edgar_host = 'ftp://ftp.sec.gov'
    path = '/edgar/full-index/{0}/QTR{1}/company.zip'.format(year, quarter)
    url = edgar_host + path
    ifile, _ = IndexFile.objects.get_or_create(
        year=year, quarter=quarter, defaults=dict(filename=path))
    if ifile.complete and not reprocess:
        return
    ifile.downloaded = timezone.now()
    ifile.save()

    unique_companies = set()
    bulk_companies = set()
    bulk_indexes = []

    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    fn = os.path.join(DATA_DIR, 'company_%d_%d.zip' % (year, quarter))
    if os.path.exists(fn) and reprocess:
        os.remove(fn)
    if not os.path.exists(fn):
        try:
            compressed_data = urllib.urlopen(url).read()
        except IOError as e:
            get_filing_list.retry()
        fileout = file(fn, 'w')
        fileout.write(compressed_data)
        fileout.close()

    zip = ZipFile(fn)
    zdata = zip.read('company.idx')
    lines = zdata.split('\n')

    for form_line in lines[10:]:
        if form_line.strip() == '':
            continue
        cik = int(form_line[74:86].strip())
        filename = form_line[98:].strip()
        form = form_line[62:74].strip()
        name = form_line[0:62].strip()
        dt = form_line[86:98].strip()
        dt = date(*map(int, dt.split('-')))

        if form in ['10-K', '10-Q', '20-F', '10-K/A', '10-Q/A', '20-F/A']:
            if not Index.objects.filter(company__cik=cik, form=form, date=dt, filename=filename).exists():
                unique_companies.add(Company(cik=cik, name=name))
                bulk_indexes.append(Index(company_id=cik, form=form, date=dt, year=year, quarter=quarter, filename=filename,))

    bulk_companies = {company for company in unique_companies
                     if not Company.objects.filter(cik=company.cik).exists()}
    if bulk_companies:
        try:
            Company.objects.bulk_create(bulk_companies, batch_size=1000)
        except:
            get_filing_list.retry()
    Index.objects.bulk_create(bulk_indexes, batch_size=2500)
    IndexFile.objects.filter(id=ifile.id).update(complete=timezone.now())


@shared_task
def import_attrs(**kwargs):
    ifile = Index.objects.get(filename=kwargs['filename'])
    total_count = kwargs['total_count']
    sub_current = 0
    sub_total = 0
    current_count = 0
    commit_freq = 300

    current_count += 1

    msg = 'Processing index %s.' % (ifile.filename,)
    print_progress(msg, current_count, total_count)

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
        Index.objects.filter(id=ifile.id).update(valid=False, error=error)

    if x is None:
        error = 'No XBRL found.'
        Index.objects.filter(id=ifile.id).update(valid=False, error=error)
        return
        
    while 1:
        try:
            company = ifile.company
            bulk_objects = set()
            sub_current = 0
            for node, sub_total in x.iter_namespace():
                sub_current += 1
                if not sub_current % commit_freq:
                    print_progress(msg,
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
                namespace, _ = Namespace.objects.get_or_create(name=ns.strip())
                attribute, _ = Attribute.objects.get_or_create(namespace=namespace,
                                                                      name=attr_name,
                                                                      defaults=dict(load=True))
                if not attribute.load:
                    continue
                unit, _ = Unit.objects.get_or_create(name=node.attrib['unitRef'].strip())
                value = (node.text or '').strip()
                if not value:
                    continue
                assert len(value.split('.')[0]) <= MAX_QUANTIZE, \
                    'Value too large, must be less than %i digits: %i %s' \
                    % (MAX_QUANTIZE, len(value), repr(value))

                Attribute.objects.filter(id=attribute.id).update(total_values_fresh=False)
                if AttributeValue.objects.filter(company=company, attribute=attribute, start_date=start_date, end_date=end_date).exists():
                    continue
                bulk_objects.add(AttributeValue(
                    company=company,
                    attribute=attribute,
                    start_date=start_date,
                    end_date=end_date,
                    value=value,
                    unit=unit,
                    filing_date=ifile.date,
                ))

            if bulk_objects:
                AttributeValue.objects.bulk_create(bulk_objects)
                bulk_objects = []

            ticker = ifile.ticker()
            Index.objects.filter(id=ifile.id).update(attributes_loaded=True, _ticker=ticker)
            Attribute.do_update()
            Unit.do_update()
            break

        except DatabaseError, e:
            print e
    print_progress('Importing attributes.', current_count, total_count)
