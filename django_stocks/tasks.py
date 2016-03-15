from __future__ import absolute_import

from datetime import date, datetime
import logging
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

from django_stocks.models import Attribute, AttributeValue, Company, Index, IndexFile, Namespace, Unit, DATA_DIR

logger = logging.getLogger(__name__)


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
        logger.info('Index file {0} already loaded'.format(ifile.filename))
        return
    ifile.downloaded = timezone.now()
    ifile.save()

    unique_companies = set()
    bulk_companies = set()
    bulk_indexes = set()

    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    fn = os.path.join(DATA_DIR, 'company_%d_%d.zip' % (year, quarter))
    if os.path.exists(fn) and reprocess:
        os.remove(fn)
    if not os.path.exists(fn):
        try:
            compressed_data = urllib.urlopen(url).read()
        except IOError as e:
            logger.warning('Could not download {0}'.format(ifile.filename))
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
                bulk_indexes.add(Index(company_id=cik, form=form, date=dt, year=year, quarter=quarter, filename=filename,))

    bulk_companies = {company for company in unique_companies
                     if not Company.objects.filter(cik=company.cik).exists()}
    if bulk_companies:
        try:
            Company.objects.bulk_create(bulk_companies, batch_size=1000)
        except Exception as e:
            logger.warning(e)
            get_filing_list.retry()
    try:
        Index.objects.bulk_create(bulk_indexes, batch_size=2500)
    except Exception as e:
        logger.warning(e)
        get_filing_list.retry()
    IndexFile.objects.filter(id=ifile.id).update(complete=timezone.now())
    time_to_complete = ifile.complete - ifile.downloaded
    logger.info('Added {0} in {1} seconds'.format(ifile.filename, time_to_complete))


@shared_task
def import_attrs(**kwargs):
    ifile = Index.objects.get(filename=kwargs['filename'])
    ifile.download(verbose=kwargs['verbose'])
    x = None
    error = None
    try:
        x = ifile.xbrl()
    except Exception, e:
        ferr = StringIO()
        traceback.print_exc(file=ferr)
        error = ferr.getvalue()
        Index.objects.filter(id=ifile.id).update(valid=False, error=error)

    if x is None:
        error = 'No XBRL found.'
        Index.objects.filter(id=ifile.id).update(valid=False, error=error)
        return
        
    while 1:
        company = ifile.company
        bulk_objects = set()
        for node in x.iter_namespace():
            matches = re.findall('^\{([^\}]+)\}(.*)$', node.tag)
            if matches:
                ns, attr_name = matches[0]
            else:
                ns = None
                attr_name = node

            context_id = node.attrib['contextRef']
            if context_id not in [x.fields['ContextForInstants'], x.fields['ContextForDurations']]:
                continue
            start_date = x.get_context_start_date(context_id)
            end_date = x.get_context_end_date(context_id)

            if not node.attrib.get('unitRef', None):
                continue

            namespace, _ = Namespace.objects.get_or_create(name=ns.strip())
            attribute, _ = Attribute.objects.get_or_create(namespace=namespace,
                                                           name=attr_name)
            unit, _ = Unit.objects.get_or_create(name=node.attrib['unitRef'].strip())
            value = (node.text or '').strip()
            if not value:
                continue

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
            bulk_objects.clear()

        Attribute.do_update()
        break
