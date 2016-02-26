from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

import models


admin.site.register(models.Namespace)


@admin.register(models.Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(models.Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'namespace',
                    'total_values',)

    search_fields = ('name',)
    readonly_fields = ('total_values',)
    

@admin.register(models.AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ('company',
                    'attribute_name',
                    'value',
                    'unit',
                    'start_date',
                    'end_date',
                    'filing_date',
                    'attribute_total_values',)

    list_filter = ('end_date',)

    search_fields = ('company__name',
                     'attribute__name',)
    
    readonly_fields = ('company',
                       'attribute',
                       'attribute_total_values',
                       'unit',)
    
    exclude = ('unit',)
    
    def company_name(self, obj=None):
        if not obj:
            return ''
        return obj.company.name
    
    def attribute_name(self, obj=None):
        if not obj:
            return ''
        return obj.attribute.name
    
    def attribute_total_values(self, obj=None):
        if not obj:
            return ''
        return obj.attribute.total_values
    attribute_total_values.admin_order_field = 'attribute__total_values'


@admin.register(models.Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('cik',
                    'name',
                    'min_date',
                    'max_date',
                    'load',)
    list_filter = ('load',)
    
    search_fields = ('cik',
                     'name',)
    
    readonly_fields = ('cik',
                       'name',
                       'filings_link',
                       'values_link',
                       'min_date',
                       'max_date',)
    
    actions = ('enable_load',
               'disable_load',)
    
    def enable_load(self, request, queryset):
        models.Company.objects.filter(cik__in=queryset).update(load=True)
        models.Index.objects.filter(company__cik__in=queryset, attributes_loaded=True).update(attributes_loaded=False)
    enable_load.short_description = 'Enable attribute loading of selected %(verbose_name_plural)s'
    
    def disable_load(self, request, queryset):
        models.Company.objects.filter(cik__in=queryset).update(load=False)
    disable_load.short_description = 'Disable attribute loading of selected %(verbose_name_plural)s'
    
    def filings_link(self, obj=None):
        if not obj:
            return ''
        ct = ContentType.objects.get_for_model(models.Index)
        list_url_name = 'admin:%s_%s_changelist' % (ct.app_label, ct.model)
        url = reverse(list_url_name) + ('?company=%s' % obj.cik)
        count = obj.filings.all().count()
        return '<a href="%s" target="_blank" class="button">View %i</a>' % (url, count)
    filings_link.short_description = 'filings'
    filings_link.allow_tags = True
    
    def values_link(self, obj=None):
        if not obj:
            return ''
        ct = ContentType.objects.get_for_model(models.AttributeValue)
        list_url_name = 'admin:%s_%s_changelist' % (ct.app_label, ct.model)
        url = reverse(list_url_name) + ('?company=%s' % obj.cik)
        count = obj.attributes.all().count()
        return '<a href="%s" target="_blank" class="button">View %i</a>' % (url, count)
    values_link.short_description = 'attributes'
    values_link.allow_tags = True


@admin.register(models.IndexFile)
class IndexFileAdmin(admin.ModelAdmin):
    list_display = ('year',
                    'quarter',
                    'downloaded',
                    'complete',)
    
    actions = ('mark_unprocessed',)
    
    def mark_unprocessed(self, request, queryset):
        models.IndexFile.objects\
            .filter(id__in=queryset.values_list('id', flat=True))\
            .update(complete=None, downloaded=None)
    mark_unprocessed.short_description = 'Mark selected %(verbose_name_plural)s as unprocessed'
    
    def get_readonly_fields(self, request, obj=None):
        exclude = []
        return [
            _.name for _ in self.model._meta.fields
            if _.name not in exclude
        ]


@admin.register(models.Index)
class IndexAdmin(admin.ModelAdmin):
    list_display = ('filename',
                    'company',
                    'cik',
                    #'ticker',
                    'form',
                    'date',
                    'quarter',
                    'attributes_loaded',
                    'valid',)

    search_fields = ('filename',
                     'company__name',)
    
    list_filter = ('attributes_loaded',
                   'valid',
                   'year',
                   'quarter',
                   'form',)
    
    readonly_fields = ('cik',
                       'xbrl_link',)
    
    def cik(self, obj=None):
        if not obj:
            return ''
        return obj.company.cik
    cik.admin_order_field = 'company__cik'
    
    def get_readonly_fields(self, request, obj=None):
        exclude = []
        return [
            _.name for _ in self.model._meta.fields
            if _.name not in exclude
        ] + list(self.readonly_fields)
