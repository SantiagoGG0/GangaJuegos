"""Deja configurado el banner de lanzamiento para GTA VI (19 de noviembre de
2026, 00:00 hora de Colombia). Solo si el juego existe y el banner todavía no
tiene un juego asignado; se cambia luego en el panel → Lanzamiento."""
import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

LAUNCH_AT = datetime.datetime(2026, 11, 19, 0, 0, tzinfo=ZoneInfo('America/Bogota'))


def forwards(apps, schema_editor):
    Juego = apps.get_model('catalog', 'Juego')
    SiteSettings = apps.get_model('catalog', 'SiteSettings')
    juego = Juego.objects.filter(slug='grand-theft-auto-vi').first()
    row = SiteSettings.objects.filter(pk=2).first()  # SiteSettings.SITE_SETTINGS_PK
    if not juego or not row or row.launch_juego_id:
        return
    row.launch_active = True
    row.launch_juego = juego
    row.launch_title = 'Grand Theft Auto VI'
    row.launch_subtitle = 'Asegura tu copia digital para PS5 y juega desde el primer día.'
    row.launch_at = LAUNCH_AT
    row.save(update_fields=['launch_active', 'launch_juego', 'launch_title', 'launch_subtitle', 'launch_at'])


class Migration(migrations.Migration):
    dependencies = [('catalog', '0018_banner_lanzamiento')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
