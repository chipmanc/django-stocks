from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

try:
    from admin_steroids.queryset import ApproxCountQuerySet
except ImportError, e:
    ApproxCountQuerySet = None

import forms
import models

class NamespaceAdmin(admin.ModelAdmin):
    
    list_display = (
        'name',
    )
    
    search_fields = (
        'name',
    )

admin.site.register(
    models.Namespace,
    NamespaceAdmin)

class UnitAdmin(admin.ModelAdmin):
    
    form = forms.UnitChangeForm
    
    list_display = (
        'name',
        'master',
    )
    
    list_filter = (
        'master',
    )
    
    readonly_fields = (
        'master',
    )
    
    search_fields = (
        'name',
    )

admin.site.register(
    models.Unit,
    UnitAdmin)

class AttributeAdmin(admin.ModelAdmin):
    
    list_display = (
        'name',
        'namespace',
        'load',
        'total_values_fresh',
        'total_values',
    )
    
    list_filter = (
        'load',
        'total_values_fresh',
    )
    
    search_fields = (
        'name',
    )
    
    readonly_fields = (
        'total_values',
    )
    
    actions = (
        'enable_load',
        'disable_load',
        'refresh_total_values',
    )
    
    def queryset(self, *args, **kwargs):
        qs = super(AttributeAdmin, self).queryset(*args, **kwargs)
        if ApproxCountQuerySet:
            qs = qs._clone(klass=ApproxCountQuerySet)
        return qs
    
    def enable_load(self, request, queryset):
        models.Attribute.objects.filter(id__in=queryset).update(load=True)
        models.Index.objects.filter(attributes_loaded=True).update(attributes_loaded=False)
    enable_load.short_description = 'Enable value loading of selected %(verbose_name_plural)s'
    
    def disable_load(self, request, queryset):
        models.Attribute.objects.filter(id__in=queryset).update(load=False)
    disable_load.short_description = 'Disable value loading of selected %(verbose_name_plural)s'
    
    def refresh_total_values(self, request, queryset):
        queryset.update(total_values_fresh=False)
        models.Attribute.do_update()
    refresh_total_values.short_description = 'Refresh to total values count of selected %(verbose_name_plural)s'

admin.site.register(
    models.Attribute,
    AttributeAdmin)

class AttributeValueAdmin(admin.ModelAdmin):
    
    list_display = (
        'company_name',
        'attribute_name',
        'value',
        'true_unit',
        'start_date',
        'end_date',
        'filing_date',
        'attribute_total_values',
    )
    
    raw_id_fields = (
        'company',
        'attribute',
    )
    
    search_fields = (
        'company__name',
        'attribute__name',
    )
    
    readonly_fields = (
        'company_name',
        'attribute_name',
        'attribute_total_values',
        'true_unit',
    )
    
    exclude = (
        'unit',
    )
    
    def queryset(self, *args, **kwargs):
        qs = super(AttributeValueAdmin, self).queryset(*args, **kwargs)
        if ApproxCountQuerySet:
            qs = qs._clone(klass=ApproxCountQuerySet)
        return qs
    
    def true_unit(self, obj=None):
        if not obj:
            return ''
        return obj.unit.true_unit
    true_unit.short_description = 'unit'
    
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

admin.site.register(
    models.AttributeValue,
    AttributeValueAdmin)

class CompanyAdmin(admin.ModelAdmin):
    
    list_display = (
        'cik',
        'name',
        'min_date',
        'max_date',
        'load',
    )
    
    list_filter = (
        'load',
    )
    
    search_fields = (
        'cik',
        'name',
        '_ticker',
    )
    
    readonly_fields = (
        'cik',
        'name',
        'filings_link',
        'values_link',
        'min_date',
        'max_date',
    )
    
    actions = (
        'enable_load',
        'disable_load',
    )
    
    def lookup_allowed(self, key, value):
        return True
    
    def queryset(self, *args, **kwargs):
        qs = super(CompanyAdmin, self).queryset(*args, **kwargs)
        if ApproxCountQuerySet:
            qs = qs._clone(klass=ApproxCountQuerySet)
        return qs
    
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

admin.site.register(
    models.Company,
    CompanyAdmin)

class IndexFileAdmin(admin.ModelAdmin):
    
    list_display = (
        'year',
        'quarter',
        'total_rows',
        'processed_rows',
        'percent_processed',
        'downloaded',
        'processed',
    )
    
    readonly_fields = (
        'percent_processed',
    )
    
    actions = (
        'mark_unprocessed',
    )
    
    def queryset(self, *args, **kwargs):
        qs = super(IndexFileAdmin, self).queryset(*args, **kwargs)
        if ApproxCountQuerySet:
            qs = qs._clone(klass=ApproxCountQuerySet)
        return qs
    
    def mark_unprocessed(self, request, queryset):
        models.IndexFile.objects\
            .filter(id__in=queryset.values_list('id', flat=True))\
            .update(processed=None, processed_rows=0)
    mark_unprocessed.short_description = 'Mark selected %(verbose_name_plural)s as unprocessed'
    
    def percent_processed(self, obj=None):
        if not obj or not obj.total_rows or not obj.processed_rows:
            return ''
        return '%.02f%%' % (obj.processed_rows/float(obj.total_rows)*100,)

admin.site.register(
    models.IndexFile,
    IndexFileAdmin)
    
class IndexAdmin(admin.ModelAdmin):
    list_display = (
        'filename',
        'company',
        'cik',
        '_ticker',
        'form',
        'date',
        'quarter',
        'attributes_loaded',
        'valid',
    )
    
    search_fields = (
        'filename',
        'company__name',
    )
    
    list_filter = (
        'attributes_loaded',
        'valid',
        'year',
        'quarter',
        'form',
    )
    
    readonly_fields = (
        'cik',
        'xbrl_link',
    )
    
    actions = (
#        'enable',
#        'disable',
    )
    
    def queryset(self, *args, **kwargs):
        qs = super(IndexAdmin, self).queryset(*args, **kwargs)
        if ApproxCountQuerySet:
            qs = qs._clone(klass=ApproxCountQuerySet)
        return qs
    
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
    
    def get_fieldsets(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        exclude = readonly_fields + ['id']
        first = ['filename']
        fields = first + readonly_fields + [
            _.name for _ in self.model._meta.fields
            if _.name not in exclude and _.name not in first
        ]
        fieldsets = (
            (None, {
                'fields': fields,
            }),
        )
        return fieldsets
    
    def enable(self, request, queryset):
        for r in queryset.iterator():
            r.enabled = True
            r.save()
    enable.short_description = 'Enable selected %(verbose_name_plural)s'
    
    def disable(self, request, queryset):
        for r in queryset.iterator():
            r.enabled = False
            r.save()
    disable.short_description = 'Disable selected %(verbose_name_plural)s'
    
admin.site.register(
    models.Index,
    IndexAdmin)
