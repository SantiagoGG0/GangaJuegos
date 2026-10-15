import csv

from django import forms
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from apps.panel.admin_site import gs_admin_site

from . import snapshot
from .models import Combo, Cover, Cupon, Divisa, GiftCard, HeroVideo, Juego, PlusPlan, SaldoCodigo, SiteEvent, SiteSettings, Testimonial, TierInfo


@admin.action(description='Marcar como activo')
def marcar_activo(modeladmin, request, queryset):
    queryset.update(active=True)
    snapshot.bump()


@admin.action(description='Marcar como inactivo')
def marcar_inactivo(modeladmin, request, queryset):
    queryset.update(active=False)
    snapshot.bump()


@admin.action(description='Marcar como destacado')
def marcar_destacado(modeladmin, request, queryset):
    queryset.update(featured=True)
    snapshot.bump()


class CoverInline(admin.StackedInline):
    model = Cover
    extra = 0
    max_num = 1
    fields = ['image', 'preview']
    readonly_fields = ['preview']

    @admin.display(description='Vista previa')
    def preview(self, obj):
        if obj and obj.image:
            return format_html('<img src="{}" style="max-width:160px;max-height:210px;border-radius:8px;border:1px solid #EADFCF;">', obj.image.url)
        return 'Sin carátula todavía — súbela aquí o desde el Gestor de carátulas.'


@admin.register(Juego, site=gs_admin_site)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ['cover_thumb', 'title', 'platform', 'genre', 'price_secondary', 'price_primary', 'active', 'featured']
    list_editable = ['active', 'featured']
    list_filter = ['platform', 'active', 'featured']
    search_fields = ['title', 'slug', 'genre']
    prepopulated_fields = {'slug': ('title',)}
    actions = [marcar_activo, marcar_inactivo, marcar_destacado]
    inlines = [CoverInline]
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'platform', 'genre')}),
        ('Precios', {'fields': ('price_secondary', 'price_primary', 'old_price_secondary', 'old_price_primary')}),
        ('Estado', {'fields': ('active', 'featured', 'tagline', 'notas')}),
    )

    @admin.display(description='Carátula')
    def cover_thumb(self, obj):
        cover = getattr(obj, 'cover', None)
        if cover and cover.image:
            return format_html('<img src="{}" style="width:34px;height:45px;object-fit:cover;border-radius:4px;">', cover.image.url)
        return '—'


@admin.register(Combo, site=gs_admin_site)
class ComboAdmin(admin.ModelAdmin):
    list_display = ['title', 'price_secondary', 'price_primary']
    filter_horizontal = ['games']
    prepopulated_fields = {'slug': ('title',)}


@admin.register(PlusPlan, site=gs_admin_site)
class PlusPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'tier', 'platform', 'months', 'price']
    list_display_links = ['id']
    list_editable = ['tier', 'platform', 'months', 'price']
    list_filter = ['platform', 'tier']


@admin.register(TierInfo, site=gs_admin_site)
class TierInfoAdmin(admin.ModelAdmin):
    list_display = ['tier', 'label', 'recommended']


@admin.register(GiftCard, site=gs_admin_site)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = ['id', 'region', 'denomination', 'price']
    list_display_links = ['id']
    list_editable = ['region', 'denomination', 'price']
    ordering = ['denomination']


@admin.action(description='Exportar clientes/cupones seleccionados a CSV')
def export_as_csv(modeladmin, request, queryset):
    field_names = [f.name for f in modeladmin.model._meta.fields]
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={modeladmin.model._meta.model_name}.csv'
    response.write('﻿')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])
    return response


@admin.register(Cupon, site=gs_admin_site)
class CuponAdmin(admin.ModelAdmin):
    list_display = ['code', 'tipo', 'valor', 'usos_actuales', 'usos_max', 'vence', 'estado']
    list_filter = ['tipo']
    search_fields = ['code']
    actions = [export_as_csv]


@admin.register(SaldoCodigo, site=gs_admin_site)
class SaldoCodigoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'monto', 'usos_max', 'usos_actuales', 'estado', 'activo', 'creado']
    list_editable = ['usos_max', 'activo']
    list_filter = ['activo']
    search_fields = ['codigo']
    readonly_fields = ['usos_actuales']


@admin.register(Divisa, site=gs_admin_site)
class DivisaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'bandera', 'pais', 'tasa', 'actualizado']
    list_editable = ['tasa']


@admin.register(HeroVideo, site=gs_admin_site)
class HeroVideoAdmin(admin.ModelAdmin):
    list_display = ['juego', 'order', 'active', 'preview']
    list_editable = ['order', 'active']
    autocomplete_fields = ['juego']

    @admin.display(description='Vista previa')
    def preview(self, obj):
        if obj.poster:
            return format_html('<img src="{}" style="width:34px;height:45px;object-fit:cover;border-radius:4px;">', obj.poster.url)
        return '—'


@admin.register(Testimonial, site=gs_admin_site)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'active']
    list_editable = ['order', 'active']
    search_fields = ['name', 'text']


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = '__all__'
        widgets = {
            'review_video_file': forms.ClearableFileInput(attrs={'accept': 'video/*'}),
        }


@admin.register(SiteSettings, site=gs_admin_site)
class SiteSettingsAdmin(admin.ModelAdmin):
    form = SiteSettingsForm
    fieldsets = (
        ('WhatsApp', {'fields': ('whatsapp_number', 'whatsapp_button_number', 'whatsapp_support_number', 'whatsapp_community_url', 'support_email')}),
        ('Pasarelas de pago (carrito)', {'fields': ('mercadopago_enabled', 'paypal_enabled')}),
        ('Código de referido (carrito)', {'fields': ('referral_enabled', 'referral_reward_pct')}),
        ('Reseñas / Instagram (home)', {'fields': (
            'review_count', 'review_video_file', 'review_video_image', 'review_video_caption', 'review_video_url',
            'instagram_handle', 'instagram_followers_label', 'instagram_active', 'instagram_url',
        )}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load_fresh()
        return self.change_view(request, str(obj.pk), extra_context=extra_context)
