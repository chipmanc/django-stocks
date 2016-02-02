from __future__ import absolute_import

from celery import shared_task
import urllib
import os
import sys
from zipfile import ZipFile
from datetime import date, datetime

from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_text
from django_stocks.models import Company, Index, IndexFile, DATA_DIR


@shared_task
def get_filing_list(year, quarter, reprocess=False):
    """
    Gets the list of filings and download locations for the given
    year and quarter.
    """
    url = ('ftp://ftp.sec.gov/edgar/full-index/%d'
           '/QTR%d/company.zip') % (year, quarter)

    # Download the data and save to a file
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    fn = os.path.join(DATA_DIR, 'company_%d_%d.zip' % (year, quarter))

    ifile, _ = IndexFile.objects.get_or_create(
        year=year, quarter=quarter, defaults=dict(filename=fn))
    if ifile.processed and not reprocess:
        return
    ifile.filename = fn

    if os.path.exists(fn) and reprocess:
        print 'Deleting old file %s.' % fn
        os.remove(fn)

    if not os.path.exists(fn):
        print 'Downloading %s.' % (url,)
        try:
            compressed_data = urllib.urlopen(url).read()
        except IOError, e:
            print 'Unable to download url: %s' % (e,)
            return
        fileout = file(fn, 'w')
        fileout.write(compressed_data)
        fileout.close()
        ifile.downloaded = timezone.now()

    if not ifile.downloaded:
        ifile.downloaded = timezone.now()
    ifile.save()
    transaction.commit()

    # Extract the compressed file
    print 'Opening index file %s.' % (fn,)
    zip = ZipFile(fn)
    zdata = zip.read('company.idx')
    # zdata = removeNonAscii(zdata)

    # Parse the fixed-length fields
    bulk_companies = []
    bulk_indexes = []
    bulk_commit_freq = 1000
    status_secs = 5
    lines = zdata.split('\n')
    i = 0
    total = len(lines)
    IndexFile.objects.filter(id=ifile.id).update(total_rows=total)
    last_status = None
    prior_ciks = set(Company.objects.all().values_list('cik', flat=True))
    print 'Found %i prior ciks.' % len(prior_ciks)
    index_add_count = 0
    company_add_count = 0
    for r in lines[10:]:  # Note, first 10 lines are useless headers.
        i += 1
        if (not reprocess and ifile.processed_rows and i < ifile.processed_rows):
            continue
        if (not last_status or ((datetime.now() - last_status).seconds >= status_secs)):
            print ('\rProcessing record ' '%i of %i (%.02f%%).') % (i, total, float(i)/total*100)
            sys.stdout.flush()
            last_status = datetime.now()
            IndexFile.objects.filter(id=ifile.id).update(processed_rows=i)
        dt = r[86:98].strip()
        if not dt:
            continue
        dt = date(*map(int, dt.split('-')))
        if r.strip() == '':
            continue
        name = r[0:62].strip()

        cik = int(r[74:86].strip())
        try:
            Company.objects.get(cik=cik)
        except:
            company_add_count += 1
            prior_ciks.add(cik)
            bulk_companies.append(Company(cik=cik, name=force_text(name, errors='replace')))

        filename = r[98:].strip()
        if Index.objects.filter(company__cik=cik, date=dt, filename=filename).exists():
            continue
        index_add_count += 1
        bulk_indexes.append(Index(
            company_id=cik,
            form=r[62:74].strip(),  # form type
            date=dt,
            year=year,
            quarter=quarter,
            filename=filename,
        ))
        if len(bulk_indexes) % bulk_commit_freq:
            if len(bulk_companies):
                Company.objects.bulk_create(bulk_companies)
                bulk_companies = []
            Index.objects.bulk_create(bulk_indexes)
            bulk_indexes = []
            transaction.commit()

    if bulk_indexes:
        if len(bulk_companies):
            Company.objects.bulk_create(bulk_companies)
            bulk_companies = []
        Index.objects.bulk_create(bulk_indexes)
    IndexFile.objects.filter(id=ifile.id).update(processed=timezone.now())
    transaction.commit()

    print '\rProcessing record %i of %i (%.02f%%).' % (total, total, 100),
    print
    print '%i new companies found.' % company_add_count
    print '%i new indexes found.' % index_add_count
    sys.stdout.flush()
    IndexFile.objects.filter(id=ifile.id).update(processed_rows=total)


@shared_task
def import_attrs():
    pass
