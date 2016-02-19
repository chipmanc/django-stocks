Django-Stocks
==========

This is a Django app that downloads all SEC filings from the EDGAR database
into your local database. It provides an admin interface to allow you to
control which indexes and attributes are loaded as well as inspect downloaded
data.

This is a fork of Chris Spencer's [django-sec](https://github.com/chrisspen/django-sec),
which is originally a fork of Luke Rosiak's [PySEC](https://github.com/lukerosiak/pysec).

Installation
------------

Install the package using pip via:

    pip install django-stocks

Django-stocks has several dependencies, you may be required to install:

* libxml2-devel
* libxslt-devel
* gcc


As this application uses celery to distribute tasks across multiple nodes, a broker will 
need to be installed.  I suggest RabbitMQ, but others are available as well. You can read 
more about celery and its requirements here:
http://www.celeryproject.org

You will need to add these lines to your settings.py:

    BROKER_URL = amqp://host
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'

Also add `django_stocks` to your `INSTALLED_APPS` and run:

    python manage.py makemigrations django_stocks
    python manage.py migrate django_stocks

Finally, you will need to have celery running in order to accept tasks off the queue.
Creating an init script is beyond the scope of this README, but you can use this command 
for testing:

    celery -A django_stocks worker -l INFO

Usage
-----

The data import process is divided into two basic commands.
First, import filing indexes for a target year by running:

    python manage.py sec_import_index --start-year=<year1> --end-year=<year2>
    
This will essentially load the "card catalog" of all companies that filed
documents between those years.

Because the list of companies and filings is enormous, by default, all
companies are configured to not download any actual filings
unless explicitly marked to do so.

To mark companies for download, to go the
company change list page, select one or more companies and run the action
"Enable attribute loading..." Then run:

    python manage.py sec_import_attrs --start-year=<year1> --end-year=<year2>  --form=10-Q,10-K
    
This will download all 10-K and 10-Q filings, extract the attributes and populate
them into the AttributeValue table accessible at:

    http://localhost:8000/admin/django_stocks/attributevalue/

Currently, this has only been tested to download and extract attributes from
10-K and 10-Q filings.

The commands support additional parameters and filters, such as to load data
for specific companies or quarters. Run `python manage help sec_import_index`
to see all options.

Future features
---------------

* Celery integration to run concurrently across a cluster of servers
* Refactor code to use better design pattern
* Create Tests
* Start Documentation
* Enable Logging
* Modify management commands to update from Edgar via day, not month
* Pep8ify
