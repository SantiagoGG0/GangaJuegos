import re
from urllib.parse import quote

from django.conf import settings

# Para qué se usa cada número (se editan en el panel → Contacto):
#   'ventas'  número principal: pedidos, carrito, asesoría
#   'boton'   botón flotante (vacío = principal)
#   'soporte' ayuda, ingreso, estado de pedidos (vacío = principal)
KINDS = ('ventas', 'boton', 'soporte')


def clean_number(value):
    return re.sub(r'\D', '', value or '')


def whatsapp_number(kind='ventas'):
    from apps.catalog.models import SiteSettings
    s = SiteSettings.load()
    main = clean_number(s.whatsapp_number) or settings.WHATSAPP_NUMBER
    if kind == 'boton':
        return clean_number(s.whatsapp_button_number) or main
    if kind == 'soporte':
        return clean_number(s.whatsapp_support_number) or main
    return main


def wa_link(text, kind='ventas'):
    return f'https://wa.me/{whatsapp_number(kind)}?text={quote(text)}'
