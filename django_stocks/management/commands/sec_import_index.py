from optparse import make_option
from datetime import date, timedelta

from django_stocks.tasks import get_filing_list

from django.core.management.base import NoArgsCommand
from django.db import transaction, connection
from django.conf import settings


def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)


class Command(NoArgsCommand):
    help = ("Download new files representing one month of 990s, "
            "ignoring months we already have. Each quarter contains hundreds "
            "of thousands of filings; will take a while to run.")
    option_list = NoArgsCommand.option_list + (
        make_option('--start-year',
                    default=None),
        make_option('--end-year',
                    default=None),
        make_option('--quarter',
                    default=None),
        make_option('--delete-prior-indexes',
                    action='store_true',
                    default=False),
        make_option('--reprocess',
                    action='store_true',
                    default=False),
        make_option('--reprocess-n-days',
                    default=14,
                    help='The number of days to automatically '
                         'redownload and reprocess index files.'),)

    def handle_noargs(self, **options):

        start_year = options['start_year']
        if start_year:
            start_year = int(start_year)
        else:
            start_year = date.today().year - 1

        end_year = options['end_year']
        if end_year:
            end_year = int(end_year) + 1
        else:
            end_year = date.today().year + 1

        reprocess = options['reprocess']

        target_quarter = options['quarter']
        if target_quarter:
            target_quarter = int(target_quarter)

        reprocess_n_days = int(options['reprocess_n_days'])

        tmp_debug = settings.DEBUG
        settings.DEBUG = False
        transaction.enter_transaction_management()
        transaction.managed(True)
        try:
            for year in range(start_year, end_year):
                for quarter in range(4):
                    if target_quarter and quarter+1 != target_quarter:
                        continue
                    quarter_start = date(year, quarter*3+1, 1)
                    reprocess_date = (quarter_start >
                            (date.today() - timedelta(days=reprocess_n_days)))
                    _reprocess = (reprocess or reprocess_date)
                    get_filing_list.delay(year, quarter+1, reprocess=_reprocess)
        finally:
            settings.DEBUG = tmp_debug
            transaction.commit()
            transaction.leave_transaction_management()
            connection.close()
