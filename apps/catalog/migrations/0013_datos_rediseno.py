"""Datos para el rediseño:

- Los cupones de monto fijo pasan de estar denominados en USD a COP (la base
  de precios de toda la tienda y del panel). Se convierten con la tasa USD
  vigente para que sigan descontando exactamente lo mismo.
- Se anuncia por defecto el cupón BIENVENIDO10 (si existe y está activo) en
  la cinta superior y la píldora flotante del rediseño.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations


def forwards(apps, schema_editor):
    Cupon = apps.get_model('catalog', 'Cupon')
    Divisa = apps.get_model('catalog', 'Divisa')
    SiteSettings = apps.get_model('catalog', 'SiteSettings')

    usd = Divisa.objects.filter(codigo='USD').first()
    rate = usd.tasa if usd and usd.tasa else Decimal('4100')
    for c in Cupon.objects.filter(tipo='monto_fijo'):
        c.valor = (Decimal(c.valor) * rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        c.save(update_fields=['valor'])

    if Cupon.objects.filter(code='BIENVENIDO10').exists():
        for row in SiteSettings.objects.all():
            if not row.promo_coupon:
                row.promo_coupon = 'BIENVENIDO10'
                row.save(update_fields=['promo_coupon'])


def backwards(apps, schema_editor):
    Cupon = apps.get_model('catalog', 'Cupon')
    Divisa = apps.get_model('catalog', 'Divisa')
    usd = Divisa.objects.filter(codigo='USD').first()
    rate = usd.tasa if usd and usd.tasa else Decimal('4100')
    for c in Cupon.objects.filter(tipo='monto_fijo'):
        c.valor = (Decimal(c.valor) / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        c.save(update_fields=['valor'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0012_rediseno_ofertas_cupones_promo'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
