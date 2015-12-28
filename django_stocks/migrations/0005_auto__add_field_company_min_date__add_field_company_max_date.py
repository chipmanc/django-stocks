# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Company.min_date'
        db.add_column(u'django_sec_company', 'min_date',
                      self.gf('django.db.models.fields.DateField')(db_index=True, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Company.max_date'
        db.add_column(u'django_sec_company', 'max_date',
                      self.gf('django.db.models.fields.DateField')(db_index=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Company.min_date'
        db.delete_column(u'django_sec_company', 'min_date')

        # Deleting field 'Company.max_date'
        db.delete_column(u'django_sec_company', 'max_date')


    models = {
        'django_sec.attribute': {
            'Meta': {'unique_together': "(('namespace', 'name'),)", 'object_name': 'Attribute', 'index_together': "(('namespace', 'name'),)"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'load': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '500', 'db_index': 'True'}),
            'namespace': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_sec.Namespace']"}),
            'total_values': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'total_values_fresh': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'django_sec.attributevalue': {
            'Meta': {'ordering': "('-attribute__total_values', '-start_date', 'attribute__name')", 'unique_together': "(('company', 'attribute', 'start_date', 'end_date'),)", 'object_name': 'AttributeValue', 'index_together': "(('company', 'attribute', 'start_date'),)"},
            'attribute': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'values'", 'to': "orm['django_sec.Attribute']"}),
            'company': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attributes'", 'to': "orm['django_sec.Company']"}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'filing_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_sec.Unit']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '40', 'decimal_places': '6'})
        },
        'django_sec.company': {
            'Meta': {'object_name': 'Company'},
            'cik': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True', 'db_index': 'True'}),
            'load': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'max_date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'min_date': ('django.db.models.fields.DateField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        },
        'django_sec.index': {
            'Meta': {'ordering': "('-date', 'filename')", 'unique_together': "(('company', 'form', 'date', 'filename', 'year', 'quarter'),)", 'object_name': 'Index', 'index_together': "(('year', 'quarter'), ('company', 'date', 'filename'))"},
            '_ticker': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '50', 'null': 'True', 'db_column': "'ticker'", 'blank': 'True'}),
            'attributes_loaded': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'company': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filings'", 'to': "orm['django_sec.Company']"}),
            'date': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'form': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '10', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quarter': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'valid': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'year': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        'django_sec.indexfile': {
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
        'django_sec.namespace': {
            'Meta': {'object_name': 'Namespace'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500', 'db_index': 'True'})
        },
        'django_sec.unit': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Unit'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'master': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200', 'db_index': 'True'}),
            'true_unit': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['django_sec.Unit']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        }
    }

    complete_apps = ['django_sec']