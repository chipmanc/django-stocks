from datetime import date, timedelta

from django.core.management.base import BaseCommand

from django_stocks.tasks import get_filing_list

# This function might not be needed
# def remove_non_ascii(s):
#     return "".join(i for i in s if ord(i) < 128)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--start-year',
                            default=date.today().year,
                            type=int)
        parser.add_argument('--end-year',
                            default=date.today().year,
                            type=int)
        parser.add_argument('--quarter',
                            default=None)
        parser.add_argument('--delete-prior-indexes',
                            action='store_true',
                            default=False)
        parser.add_argument('--reprocess',
                            action='store_true',
                            default=False)
        parser.add_argument('--reprocess-n-days',
                            default=14,
                            type=int,
                            help='The number of days to automatically '
                                 'redownload and reprocess index files.')
        # help = ("Download new files representing one month of 990s, "
        #        "ignoring months we already have. Each quarter contains hundreds "
        #        "of thousands of filings; will take a while to run.")

    def handle(self, *args, **options):
        reprocess = options['reprocess']
        reprocess_n_days = options['reprocess_n_days']
        target_quarter = options['quarter']
        if target_quarter:
            target_quarter = int(target_quarter)

        for year in range(options['start_year'], options['end_year']):
            for quarter in range(4):
                if target_quarter and quarter+1 != target_quarter:
                    continue
                quarter_start = date(year, quarter*3+1, 1)
                reprocess_date = (quarter_start >
                                  (date.today() - timedelta(days=reprocess_n_days)))
                _reprocess = (reprocess or reprocess_date)
                get_filing_list.delay(year, quarter+1, reprocess=_reprocess)
