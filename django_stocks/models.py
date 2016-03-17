import logging
import os
import sys
import urllib
import zipfile

from django.conf import settings
from django.db import models
from django.db.models import Min, Max
from django.utils.translation import ugettext, ugettext_lazy as _

from django_stocks import xbrl

import constants as c
from .settings import DATA_DIR
from .utils import prep_fs_download, suppress

logger = logging.getLogger(__name__)

class Namespace(models.Model):
    """
    Represents an XBRL namespace used to segment attribute names.
    """
    
    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        db_index=True,
        unique=True)
    
    
    def __unicode__(self):
        return self.name

class Unit(models.Model):
    """
    Represents a numeric unit.
    """
    
    name = models.CharField(
        max_length=200,
        blank=False,
        null=False,
        db_index=True,
        unique=True)
    
    class Meta:
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    

class Attribute(models.Model):
    """
    Represents a financial attribute tag.
    """
    
    namespace = models.ForeignKey('Namespace')
    
    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        db_index=True)
    
    total_values = models.PositiveIntegerField(
        blank=True,
        null=True,
        editable=True)
    
    total_values_fresh = models.BooleanField(
        default=False,
        verbose_name='fresh')
    
    class Meta:
        unique_together = (('namespace', 'name'),)
        index_together = (('namespace', 'name'),)
    
    def __unicode__(self):
        return '%s' % (self.name)
    
    @classmethod
    def do_update(cls, *args, **kwargs):
        q = cls.objects.filter(total_values_fresh=False).only('id', 'name')
        total = q.count()
        for r in q.iterator():
            total_values = AttributeValue.objects.filter(attribute__name=r.name).count()
            cls.objects.filter(id=r.id).update(
                total_values=total_values,
                total_values_fresh=True)


class AttributeValue(models.Model):
    
    company = models.ForeignKey('Company', related_name='attributes')
    attribute = models.ForeignKey('Attribute', related_name='values')
    
    # Inspecting several XBRL samples, no digits above 12 characters
    # or decimals above 5 were found, so I've started there and added
    # a little more to handle future increases.
    value = models.DecimalField(
        max_digits=c.MAX_DIGITS,
        decimal_places=c.MAX_DECIMALS,
        blank=False,
        null=False)
    
    unit = models.ForeignKey('Unit')
    
    start_date = models.DateField(
        blank=False,
        null=False,
        db_index=True,
        help_text=_('''If attribute implies a duration, this is the date
            the duration begins. If the attribute implies an instance, this
            is the exact date it applies to.'''))
    
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text=_('''If this attribute implies a duration, this is the date
            the duration ends.'''))
    
    filing_date = models.DateField(
        blank=False,
        null=False,
        help_text=_('The date this information became publically available.'))
    
    class Meta:
        ordering = ('-attribute__total_values', '-start_date', 'attribute__name')
        unique_together = (('company', 'attribute', 'start_date', 'end_date'),)
        index_together = (('company', 'attribute', 'start_date'),)

    def __hash__(self):
        return hash((self.company, self.attribute, self.value, self.start_date, self.end_date))

    def __eq__(self, other):
        return self == other
        
    def __unicode__(self):
        return '%s %s=%s %s on %s' % (
            self.company,
            self.attribute.name,
            self.value,
            self.unit,
            self.start_date,
        )

class IndexFile(models.Model):
    
    year = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    quarter = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    filename = models.CharField(max_length=200, blank=False, null=False)
    downloaded = models.DateTimeField(blank=True, null=True)
    complete = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ('-year', 'quarter')
        unique_together = (('year', 'quarter'),)

class Company(models.Model):

    cik = models.IntegerField(
        db_index=True,
        primary_key=True,
        help_text=_('Central index key that uniquely identifies a filing entity.'))
    
    name = models.CharField(
        max_length=100,
        db_index=True,
        blank=False,
        null=False,
        help_text=_('The name of the company.'))
    
    min_date = models.DateField(
        blank=True,
        null=True,
        editable=False,
        db_index=True,
        help_text=_('''The oldest date of associated SEC Edgar filings
            for this company.'''))
    
    max_date = models.DateField(
        blank=True,
        null=True,
        editable=False,
        db_index=True,
        help_text=_('''The most recent date of associated SEC Edgar filings
            for this company.'''))

    ticker = models.CharField(
        max_length=15,
        db_index=True,
        db_column='ticker',
        verbose_name=_('ticker'),
        blank=True,
        null=True,
        help_text=_('''Trading symbol of the security.'''))
    
    class Meta:
        verbose_name_plural = _('companies')
        ordering = ('name',)
    
    def __unicode__(self):
        return self.name
    
#    def save(self, *args, **kwargs):
#        if self.cik:
#            try:
#                old = type(self).objects.get(cik=self.cik)
#                
#                aggs = self.attributes.all()\
#                    .aggregate(Min('start_date'), Max('start_date'))
#                self.min_date = aggs['start_date__min']
#                self.max_date = aggs['start_date__max']
#                
#                if not old.load and self.load:
#                    # If we just flag this company for loading then
#                    # flag this company's indexes for loading.
#                    Index.objects.filter(
#                        company=self, attributes_loaded=True
#                    ).update(attributes_loaded=False)
#            except type(self).DoesNotExist:
#                pass
#        super(Company, self).save(*args, **kwargs)
    
class Index(models.Model):
    company = models.ForeignKey(
        'Company',
        related_name='filings')
    
    form = models.CharField(
        max_length=10,
        blank=True,
        db_index=True,
        verbose_name=_('form type'),
        help_text=_('The type of form the document is classified as.'))
    
    date = models.DateField(
        blank=False,
        null=False,
        db_index=True,
        verbose_name=_('date filed'),
        help_text=_('The date the item was filed with the SEC.'))
    
    filename = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        db_index=True,
        help_text=_('The name of the associated financial filing.'))
    
    year = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    quarter = models.IntegerField(
        blank=False,
        null=False,
        db_index=True)
    
    attributes_loaded = models.BooleanField(default=False, db_index=True)
    
    valid = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_('If false, errors were encountered trying to parse the associated files.'))
    
    error = models.TextField(blank=True, null=True)

    def __hash__(self):
        return hash((self.company, self.form, self.filename, self.year))

    def __eq__(self, other):
        return self == other
    
    class Meta:
        verbose_name_plural = _('indices')
        # Note, filenames are not necessarily unique.
        # Filenames may be listed more than once under a different
        # form type.
        unique_together = (('company', 'form', 'date', 'filename', 'year', 'quarter'),)
        index_together = (('year', 'quarter'),
                          ('company', 'date', 'filename'),)
        ordering = ('-date', 'filename')
    
    @property
    def xbrl_link(self):
        directory, fn = os.path.split(self.filename)
        directory += '/' + fn[:-4].replace('-','')
        fn = fn[:-4] + '-xbrl.zip'
        filename = os.path.join(directory, fn)
        xbrl_link = 'http://www.sec.gov/Archives/%s' % filename
        return xbrl_link

    @property
    def html_link(self):
        return 'http://www.sec.gov/Archives/%s' % self.filename

    @property
    def local_path(self):
        return os.path.join(DATA_DIR, str(self.company.cik))
        
    def xbrl_localpath(self):
        _, fn = os.path.split(self.xbrl_link)
        files = os.listdir('.')
        if fn not in files:
            return None, None
        zf = zipfile.ZipFile(fn)
        xml = sorted([elem for elem in zf.namelist() if elem.endswith('.xml')], key=len)
        if not len(xml):
            return None, None
        return xml[0], zf.open

    def xbrl(self):
        with suppress(OSError), prep_fs_download(xbrl_link) as fn:
            urllib.urlretrieve(self.xbrl_link, fn)

        filepath, open_method = self.__xbrl_localpath()
        if not filepath:
            raise IOError
        x = xbrl.XBRL(filepath, opener=open_method)
        return x

    __xbrl_localpath = xbrl_localpath
