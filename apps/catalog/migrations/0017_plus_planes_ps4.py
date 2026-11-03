"""Crea los planes PS Plus de PS4 copiando los de PS5 (mismos planes, meses y
precios) como punto de partida. Los precios se ajustan luego en el panel →
PS Plus. No toca planes PS4 que ya existan."""
from django.db import migrations


def forwards(apps, schema_editor):
    PlusPlan = apps.get_model('catalog', 'PlusPlan')
    for p in PlusPlan.objects.filter(platform='PS5'):
        PlusPlan.objects.get_or_create(tier=p.tier, platform='PS4', months=p.months, defaults={'price': p.price})


class Migration(migrations.Migration):
    dependencies = [('catalog', '0016_resenas_parafraseadas')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
