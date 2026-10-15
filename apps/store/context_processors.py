import json

from apps.catalog import snapshot
from apps.catalog.models import Cupon, Divisa, SiteSettings
from apps.catalog.pricing import iso_label
from apps.orders.cart import Cart

from . import constants as C

SOCIAL_NAMES = [
    'Andrés', 'Laura', 'Camilo', 'Valentina', 'Sebastián', 'Daniela', 'Juan', 'Mariana',
    'Santiago', 'Carolina', 'Kevin', 'Nicolás', 'Paola', 'Yeixon', 'Esteban', 'Luisa',
    'Diego', 'Camila', 'Martín', 'Sofía', 'José', 'Pablo',
]

SOCIAL_PLACES = [
    ('Bogotá', 'COP'), ('Medellín', 'COP'), ('Cali', 'COP'), ('Barranquilla', 'COP'), ('Bucaramanga', 'COP'),
    ('Caracas', 'VES'), ('Maracaibo', 'VES'), ('Quito', 'USDEC'), ('Guayaquil', 'USDEC'),
    ('Ciudad de México', 'MXN'), ('Guadalajara', 'MXN'), ('Monterrey', 'MXN'), ('Lima', 'PEN'), ('Arequipa', 'PEN'),
    ('Santiago', 'CLP'), ('Buenos Aires', 'ARS'), ('Córdoba', 'ARS'), ('Asunción', 'PYG'), ('Miami', 'USD'),
]


def _divisas():
    try:
        return list(Divisa.objects.all())
    except Exception:  # noqa: BLE001
        return []


def _countries(current_code):
    divisas = list(snapshot.cached('divisas', _divisas))
    order = {c: i for i, c in enumerate(C.COUNTRY_ORDER)}
    divisas.sort(key=lambda d: order.get(d.codigo, 99))
    return [{
        'code': d.codigo, 'iso': iso_label(d.codigo), 'name': d.pais,
        'flag': C.FLAGS.get(d.codigo, '#A9B8D6'), 'dial': C.DIALS.get(d.codigo, ''),
        'on': d.codigo == current_code,
    } for d in divisas]


def promo_coupon(settings_row=None):
    """Cupón anunciado en la cinta y en la píldora flotante (si está activo)."""
    settings_row = settings_row or SiteSettings.load()
    code = (settings_row.promo_coupon or '').strip()
    if not code:
        return None
    cupon = Cupon.objects.filter(code__iexact=code).first()
    if not cupon or cupon.estado != 'Activo':
        return None
    off = cupon.valor_display + ' off'
    return {'code': cupon.code, 'off': off, 'label': f'{cupon.code} · {off}'}


def genre_count(games, genre):
    g = genre.lower()
    return sum(1 for x in games if g in x.genre.lower())


def _menu_data(currency):
    """Datos del menú, mega-menú y toast que dependen del catálogo. Se calculan
    una vez por versión del catálogo y divisa (ver apps.catalog.snapshot)."""
    games = snapshot.active_games()
    shaped = snapshot.shaped_games(currency)
    genres = [{'label': gn, 'count': genre_count(games, gn)} for gn in C.GENRES]
    deal_games = sorted((g for g in games if g.discount_percent > 0), key=lambda g: -g.discount_percent)
    feat_obj = next((g for g in games if g.featured), None) or (deal_games[0] if deal_games else (games[0] if games else None))
    toast = {
        'names': SOCIAL_NAMES,
        'places': [{'city': city, 'flag': C.FLAGS.get(code, '#A9B8D6')} for city, code in SOCIAL_PLACES],
        'games': [{'title': g.title, 'cover': shaped[g.pk]['cover_bg']} for g in games[:60]],
    }
    return {
        'plats': [{'label': p, 'count': f'{sum(1 for g in games if p in g.platform)} juegos',
                   'url': f'/catalogo/?platform={p}'} for p in ('PS5', 'PS4')],
        'genres': [g for g in genres if g['count']],
        'feat': shaped[feat_obj.pk] if feat_obj else None,
        'deals3': [shaped[g.pk] for g in deal_games[:3]],
        'toast_json': json.dumps(toast, ensure_ascii=False).replace('<', '\\u003c'),
    }


def global_context(request):
    from .whatsapp import wa_link, whatsapp_number

    cart = Cart(request)
    user = getattr(request, 'user', None)
    is_admin = bool(user and user.is_authenticated and getattr(user, 'role', None) == 'admin')
    settings_row = SiteSettings.load()

    pixel_event = request.session.pop('pixel_event', None)
    pixel_event_json = json.dumps(pixel_event).replace('<', '\\u003c') if pixel_event else None

    base = {
        'cart_count': len(cart),
        'whatsapp_number_digits': whatsapp_number(),
        'support_email': settings_row.support_email,
        'is_admin': is_admin,
        'whatsapp_float_link': wa_link('Hola, tengo una pregunta sobre Ganga Juegos.'),
        'whatsapp_advisor_link': wa_link('Hola, quiero que un asesor me ayude a elegir entre cuenta primaria y secundaria.'),
        'whatsapp_help_link': wa_link('Hola, tengo una pregunta y no encontré la respuesta en la página.'),
        'whatsapp_login_link': wa_link('Hola, tengo problemas para ingresar a mi cuenta de Ganga Juegos.'),
        'pixel_event_json': pixel_event_json,
    }
    # el panel de administración no usa nada de lo de abajo (menús, monedas,
    # catálogo) — se evita consultarlo en cada página del panel.
    if request.path.startswith('/admin'):
        return base

    from apps.catalog.offers import expire_offers
    expire_offers()

    current_code = request.session.get('currency', 'COP')
    countries = _countries(current_code)
    current = next((c for c in countries if c['on']), None) or (countries[0] if countries else
                                                                {'code': 'COP', 'iso': 'COP', 'name': 'Colombia', 'flag': C.FLAGS['COP'], 'dial': '+57'})
    if current_code not in {c['code'] for c in countries}:
        current_code = current['code']

    url_name = getattr(getattr(request, 'resolver_match', None), 'url_name', None)
    nav_key = {'catalog': 'catalog', 'deals': 'deals', 'combos': 'combos', 'plus': 'plus', 'giftcards': 'gift'}.get(url_name)
    nav = [
        {'key': 'catalog', 'label': 'Catálogo', 'url': '/catalogo/', 'sub': True},
        {'key': 'deals', 'label': 'Ofertas', 'url': '/ofertas/', 'sub': True},
        {'key': 'combos', 'label': 'Combos', 'url': '/combos/', 'sub': False},
        {'key': 'plus', 'label': 'PS Plus', 'url': '/plus/', 'sub': False},
        {'key': 'gift', 'label': 'Gift cards', 'url': '/tarjetas-regalo/', 'sub': False},
    ]
    for n in nav:
        n['active'] = n['key'] == nav_key

    menu = snapshot.cached(('menu', current_code), lambda: _menu_data(current_code))
    promo = promo_coupon(settings_row)

    names = [c['name'] for c in countries]
    countries_text = (', '.join(names[:-1]) + ' y ' + names[-1]) if len(names) > 1 else ''.join(names)

    base.update({
        'currencies': countries,
        'cur': current,
        'current_currency': current_code,
        'country_count': len(countries),
        'countries_text': countries_text,
        'nav': nav,
        'nav_key': nav_key,
        'mega_plats': menu['plats'],
        'mega_genres': menu['genres'],
        'mega_feat': menu['feat'],
        'mega_deals3': menu['deals3'],
        'deal_links': [
            {'label': 'Todas las ofertas', 'url': '/ofertas/'},
            {'label': 'Ofertas PS5', 'url': '/ofertas/?platform=PS5'},
            {'label': 'Ofertas PS4', 'url': '/ofertas/?platform=PS4'},
            {'label': 'Mayor descuento', 'url': '/ofertas/?sort=Mayor+descuento'},
        ],
        'promo': promo,
        'overlay_toast': url_name in ('home', 'catalog', 'deals', 'combos', 'plus', 'giftcards'),
        'overlay_promo': bool(promo) and url_name in ('home', 'catalog', 'deals'),
        'toast_json': menu['toast_json'],
        'whatsapp_channel_link': settings_row.whatsapp_community_url or wa_link('Hola, quiero unirme al canal de ofertas de Ganga Juegos.'),
        'instagram_url': settings_row.instagram_url,
    })
    return base
