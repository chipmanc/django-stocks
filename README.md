Django-SEC
==========

This is a Django app that downloads all SEC filings from the EDGAR database
into your local database. It provides an admin interface to allow you to
control which indexes and attributes are loaded as well as inspect downloaded
data.

This is a fork of Chris Spencer's django-sec (https://github.com/chrisspen/django-sec),
which is originally a fork of Luke Rosiak's [PySEC](https://github.com/lukerosiak/pysec).

Installation
------------

Install the package using pip via:

    pip install https://github.com/chipmanc/django-sec

then add `django_sec` to your `INSTALLED_APPS` and run:

    python manage.py migrate django_sec

Usage
-----

The data import process is divided into two basic commands.

First, import filing indexes for a target year by running:

    python manage.py sec_import_index --start-year=<year1> --end-year=<year2>
    
This will essentially load the "card catalog" of all companies that filed
documents between those years.

If you're running this on the devserver, you can monitor import progress at:

    http://localhost:8000/admin/django_sec/indexfile/
    
and see the loaded indexes and companies at:

    http://localhost:8000/admin/django_sec/index/
    http://localhost:8000/admin/django_sec/company/

Because the list of companies and filings is enormous, by default, all
companies are configured to not download any actual filings
unless explicitly marked to do so.

To mark companies for download, to go the
company change list page, select one or more companies and run the action
"Enable attribute loading..." Then run:

    python manage.py sec_import_attrs --start-year=<year1> --end-year=<year2>  --form=10-Q,10-K
    
This will download all 10-K and 10-Q filings, extract the attributes and populate
them into the AttributeValue table accessible at:

    http://localhost:8000/admin/django_sec/attributevalue/

Currently, this has only been tested to download and extract attributes from
10-K and 10-Q filings.

The commands support additional parameters and filters, such as to load data
for specific companies or quarters. Run `python manage help sec_import_index`
to see all options.
