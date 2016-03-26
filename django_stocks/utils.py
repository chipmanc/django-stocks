import os
from urlparse import urlparse

from django_stocks.settings import DATA_DIR


class suppress(object):
    '''
    Context manager to suppress errors
    '''

    def __init__(self, *args):
        self.args = args

    def __enter__(self):
        pass

    def __exit__(self, etype, exc, tb):
        if etype in self.args:
            return True


class prep_fs_download(object):
    '''
    Context manager to create directories needed for URL.
    '''

    def __init__(self, url):
        self.url = url
        self.scheme, self.host, self.path = urlparse(self.url)[:3]

    def __enter__(self):
        dirpath, fn = os.path.split(self.path)
        localpath = os.path.join(DATA_DIR, dirpath[1:])
        with suppress(OSError):
            os.makedirs(localpath)
        return os.path.join(localpath, fn)

    def __exit__(self, etype, exc, tb):
        return


def lookup_cik(ticker, name=None):
    """
    Given a ticker symbol, retrieves the CIK.
    """
    ticker = ticker.strip().upper()

    # First try the SEC. In theory, should for all known symbols, even
    # deactivated ones. In practice, fails to work for many, even active ones.
    url = 'http://www.sec.gov/cgi-bin/browse-edgar?CIK={cik}&owner=exclude&Find=Find+Companies&action=getcompany'.format(cik=ticker)
    #print 'url1:',url
    #response = urllib2.urlopen(url)
    request = urllib2.Request(url=url)
    response = urllib2.urlopen(request)
    data = response.read()
    try:
        match = re.finditer('CIK=([0-9]+)', data).next()
        return match.group().split('=')[-1]
    except StopIteration:
        pass

    # Next, try SEC's other CIK lookup form.
    # It doesn't always work with just the ticker, so we also need to pass in
    # company name but it's the next most accurate after the first.
    # Unfortunately, this search is sensitive to punctuation in the company
    # name, which we might not have stored correctly.
    # So we start searching with everything we have, and then backoff to widen
    # the search.
    name = (name or '').strip()
    name = ''.join(_ for _ in (name or '').strip() if ord(_) < 128)
    if name:
        name_parts = name.split(' ')
        for i in xrange(len(name_parts)):
            url = 'http://www.sec.gov/cgi-bin/cik.pl.c?company={company}'.format(company='+'.join(name_parts[:-(i + 1)]))
#            response = urllib2.urlopen(url)
            request = urllib2.Request(url=url)
            response = urllib2.urlopen(request)
            data = response.read()
            matches = re.findall('CIK=([0-9]+)', data)
            if len(matches) == 1:
                return matches[0]

    # If the SEC search doesn't find anything, then try Yahoo.
    # Should work for all active symbols, but won't work for any deactive
    # symbols.
    url = 'http://finance.yahoo.com/q/sec?s={symbol}+SEC+Filings'.format(symbol=ticker)
    #print 'url2:',url
#    response = urllib2.urlopen(url)
    request = urllib2.Request(url=url)
    response = urllib2.urlopen(request)
    data = response.read()
    try:
        match = re.finditer('search/\?cik=([0-9]+)', data).next()
        return match.group().split('=')[-1]
    except StopIteration:
        pass

