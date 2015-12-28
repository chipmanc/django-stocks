# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Namespace'
        db.create_table(u'django_sec_namespace', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=500, db_index=True)),
        ))
        db.send_create_signal(u'django_sec', ['Namespace'])

        # Adding model 'Unit'
        db.create_table(u'django_sec_unit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200, db_index=True)),
            ('true_unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_sec.Unit'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('master', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'django_sec', ['Unit'])

        # Adding model 'Attribute'
        db.create_table(u'django_sec_attribute', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('namespace', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_sec.Namespace'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=500, db_index=True)),
            ('load', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('total_values', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('total_values_fresh', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'django_sec', ['Attribute'])

        # Adding unique constraint on 'Attribute', fields ['namespace', 'name']
        db.create_unique(u'django_sec_attribute', ['namespace_id', 'name'])

        # Adding index on 'Attribute', fields ['namespace', 'name']
        db.create_index(u'django_sec_attribute', ['namespace_id', 'name'])

        # Adding model 'AttributeValue'
        db.create_table(u'django_sec_attributevalue', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('company', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attributes', to=orm['django_sec.Company'])),
            ('attribute', self.gf('django.db.models.fields.related.ForeignKey')(related_name='values', to=orm['django_sec.Attribute'])),
            ('value', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=6)),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['django_sec.Unit'])),
            ('start_date', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('filing_date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal(u'django_sec', ['AttributeValue'])

        # Adding unique constraint on 'AttributeValue', fields ['company', 'attribute', 'start_date', 'end_date']
        db.create_unique(u'django_sec_attributevalue', ['company_id', 'attribute_id', 'start_date', 'end_date'])

        # Adding index on 'AttributeValue', fields ['company', 'attribute', 'start_date']
        db.create_index(u'django_sec_attributevalue', ['company_id', 'attribute_id', 'start_date'])

        # Adding model 'IndexFile'
        db.create_table(u'django_sec_indexfile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('year', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('quarter', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('total_rows', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('processed_rows', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('downloaded', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('processed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'django_sec', ['IndexFile'])

        # Adding unique constraint on 'IndexFile', fields ['year', 'quarter']
        db.create_unique(u'django_sec_indexfile', ['year', 'quarter'])

        # Adding model 'Company'
        db.create_table(u'django_sec_company', (
            ('cik', self.gf('django.db.models.fields.IntegerField')(primary_key=True, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('load', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
        ))
        db.send_create_signal(u'django_sec', ['Company'])

        # Adding model 'Index'
        db.create_table(u'django_sec_index', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('company', self.gf('django.db.models.fields.related.ForeignKey')(related_name='filings', to=orm['django_sec.Company'])),
            ('form', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=10, blank=True)),
            ('date', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('filename', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('year', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('quarter', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('attributes_loaded', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('valid', self.gf('django.db.models.fields.BooleanField')(default=True, db_index=True)),
            ('error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'django_sec', ['Index'])

        # Adding unique constraint on 'Index', fields ['company', 'form', 'date', 'filename', 'year', 'quarter']
        db.create_unique(u'django_sec_index', ['company_id', 'form', 'date', 'filename', 'year', 'quarter'])

        # Adding index on 'Index', fields ['year', 'quarter']
        db.create_index(u'django_sec_index', ['year', 'quarter'])


    def backwards(self, orm):
        # Removing index on 'Index', fields ['year', 'quarter']
        db.delete_index(u'django_sec_index', ['year', 'quarter'])

        # Removing unique constraint on 'Index', fields ['company', 'form', 'date', 'filename', 'year', 'quarter']
        db.delete_unique(u'django_sec_index', ['company_id', 'form', 'date', 'filename', 'year', 'quarter'])

        # Removing unique constraint on 'IndexFile', fields ['year', 'quarter']
        db.delete_unique(u'django_sec_indexfile', ['year', 'quarter'])

        # Removing index on 'AttributeValue', fields ['company', 'attribute', 'start_date']
        db.delete_index(u'django_sec_attributevalue', ['company_id', 'attribute_id', 'start_date'])

        # Removing unique constraint on 'AttributeValue', fields ['company', 'attribute', 'start_date', 'end_date']
        db.delete_unique(u'django_sec_attributevalue', ['company_id', 'attribute_id', 'start_date', 'end_date'])

        # Removing index on 'Attribute', fields ['namespace', 'name']
        db.delete_index(u'django_sec_attribute', ['namespace_id', 'name'])

        # Removing unique constraint on 'Attribute', fields ['namespace', 'name']
        db.delete_unique(u'django_sec_attribute', ['namespace_id', 'name'])

        # Deleting model 'Namespace'
        db.delete_table(u'django_sec_namespace')

        # Deleting model 'Unit'
        db.delete_table(u'django_sec_unit')

        # Deleting model 'Attribute'
        db.delete_table(u'django_sec_attribute')

        # Deleting model 'AttributeValue'
        db.delete_table(u'django_sec_attributevalue')

        # Deleting model 'IndexFile'
        db.delete_table(u'django_sec_indexfile')

        # Deleting model 'Company'
        db.delete_table(u'django_sec_company')

        # Deleting model 'Index'
        db.delete_table(u'django_sec_index')


    models = {
        u'django_sec.attribute': {
            'Meta': {'unique_together': "(('namespace', 'name'),)", 'object_name': 'Attribute', 'index_together': "(('namespace', 'name'),)"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'load': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '500', 'db_index': 'True'}),
            'namespace': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['django_sec.Namespace']"}),
            'total_values': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_values_fresh': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'django_sec.attributevalue': {
            'Meta': {'ordering': "('-attribute__total_values', '-start_date', 'attribute__name')", 'unique_together': "(('company', 'attribute', 'start_date', 'end_date'),)", 'object_name': 'AttributeValue', 'index_together': "(('company', 'attribute', 'start_date'),)"},
            'attribute': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'values'", 'to': u"orm['django_sec.Attribute']"}),
            'company': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attributes'", 'to': u"orm['django_sec.Company']"}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'filing_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['django_sec.Unit']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '6'})
        },
        u'django_sec.company': {
            'Meta': {'object_name': 'Company'},
            'cik': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True', 'db_index': 'True'}),
            'load': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        u'django_sec.index': {
            'Meta': {'unique_together': "(('company', 'form', 'date', 'filename', 'year', 'quarter'),)", 'object_name': 'Index', 'index_together': "(('year', 'quarter'),)"},
            'attributes_loaded': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'company': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filings'", 'to': u"orm['django_sec.Company']"}),
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'form': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quarter': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'django_sec.indexfile': {
            'Meta': {'ordering': "('year', 'quarter')", 'unique_together': "(('year', 'quarter'),)", 'object_name': 'IndexFile'},
            'downloaded': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'processed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'processed_rows': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'quarter': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'total_rows': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'django_sec.namespace': {
            'Meta': {'object_name': 'Namespace'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500', 'db_index': 'True'})
        },
        u'django_sec.unit': {
            'Meta': {'object_name': 'Unit'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'}),
            'true_unit': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['django_sec.Unit']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        }
    }

    complete_apps = ['django_sec']