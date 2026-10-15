from urllib.parse import quote

from django.conf import settings


def whatsapp_number():
    from apps.catalog.models import SiteSettings
    number = SiteSettings.load().whatsapp_number.strip()
    return number or settings.WHATSAPP_NUMBER


def wa_link(text):
    return f'https://wa.me/{whatsapp_number()}?text={quote(text)}'
