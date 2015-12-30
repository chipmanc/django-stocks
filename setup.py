#!/usr/bin/env python
import os
import urllib

from setuptools import setup, find_packages, Command

import django_stocks

setup(
    name = "django-stocks",
    version = django_stocks.__version__,
    packages = find_packages(),
    author = "Chris Chipman",
    author_email = "chipmanc@bellsouth.net",
    description = "Parse XBRL filings from the SEC's EDGAR in Python",
    license = "LGPL",
    url = "https://github.com/chipmanc/django-stocks",
    keywords = ["django", "stocks", "SEC"],
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
    install_requires = ['Django==1.6.0', 'lxml'],
)
