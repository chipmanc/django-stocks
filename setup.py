#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name = "django-stocks",
    version = "0.6.1",
    packages = find_packages(),
    author = "Chris Chipman",
    author_email = "chipmanc@bellsouth.net",
    description = "Parse XBRL filings from the SEC's EDGAR in Python",
    license = "LGPL",
    url = "https://github.com/chipmanc/django-stocks",
    keywords = ["django", "stocks", "SEC", "finance", "investment"],
    classifiers = [
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    zip_safe = False,
    install_requires = ['Django>=1.8.0',
                        'lxml',
                        'mock',
                        'celery==3.1.18',
                        'MySQL-python==1.2.5'],
)
