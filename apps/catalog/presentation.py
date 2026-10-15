"""Arma el diccionario de presentación de un Juego para las plantillas del
rediseño: precios primaria/secundaria en la divisa elegida, precio anterior,
badge de descuento y fondo de carátula (imagen real o patrón rayado de
respaldo, el mismo del diseño, con un tono determinista por título)."""
from .pricing import money

# degradados de marca del rediseño
GRAD = 'linear-gradient(90deg,#FC3C00,#FC5F01 35%,#FC8B01 70%,#FCC602)'
PLUS_ART = 'linear-gradient(135deg,#FCC602,#FC8B01)'
GIFT_ART = 'linear-gradient(135deg,#0A2B66,#1A4A9E)'
GIFT_ARTS = [
    '#FCC602',
    'linear-gradient(135deg,#FCC602,#FC8B01)',
    'linear-gradient(135deg,#FCC602,#FC5F01)',
    'linear-gradient(135deg,#FC8B01,#FC5F01)',
    'linear-gradient(135deg,#FC8B01,#FC3C00)',
    'linear-gradient(135deg,#FC5F01,#FC3C00)',
    'linear-gradient(135deg,#FC3C00,#C93000)',
]


def initials(title):
    words = [w for w in title.split() if w]
    return ''.join(w[0] for w in words[:2]).upper() or '??'


def _hash(text):
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def placeholder_cover(title):
    hue = _hash(title) % 360
    return (f'repeating-linear-gradient(135deg, oklch(0.88 0.05 {hue}) 0 8px, '
            f'oklch(0.84 0.06 {hue}) 8px 16px)')


def cover_url(juego):
    cover = getattr(juego, 'cover', None)
    try:
        return cover.image.url if cover and cover.image else ''
    except ValueError:
        return ''


def cover_background(juego):
    """Declaración CSS `background:...` lista para un atributo style."""
    url = cover_url(juego)
    if url:
        return f"background:#0A2B66 url('{url}') center/cover no-repeat"
    return f'background:{placeholder_cover(juego.title)}'


def shape_game(juego, mode='Primaria', currency='COP'):
    """`mode` se conserva por compatibilidad: el rediseño siempre muestra
    ambos precios (primaria y secundaria) y el "desde" es la secundaria."""
    url = cover_url(juego)
    pct = juego.discount_percent
    old = juego.old_price_primary if juego.old_price_primary and juego.old_price_primary > juego.price_primary else None
    return {
        'obj': juego,
        'pk': juego.pk,
        'slug': juego.slug,
        'url': f'/juego/{juego.slug}/',
        'title': juego.title,
        'plat': juego.platform,
        'platform': juego.platform,
        'genre': juego.genre,
        'initials': initials(juego.title),
        'has_cover': bool(url),
        'cover_url': url,
        'cover_bg': cover_background(juego),
        'prim': money(juego.price_primary, currency),
        'sec': money(juego.price_secondary, currency),
        'from': money(juego.price_secondary, currency),
        'old': money(old, currency) if old else '',
        'has_old': bool(old),
        'has_disc': pct > 0,
        'disc': f'-{pct}%' if pct > 0 else '',
        'disc_pct': pct,
        'prim_cop': juego.price_primary,
        'sec_cop': juego.price_secondary,
        'featured': juego.featured,
        'savings': money(juego.price_primary - juego.price_secondary, currency),
    }


def shape_queryset(qs, mode='Primaria', currency='COP'):
    return [shape_game(g, mode, currency) for g in qs]
