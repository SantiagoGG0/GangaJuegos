import gzip
import json
import re

from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.catalog import snapshot
from apps.catalog.models import Juego
from apps.catalog.presentation import GIFT_ARTS, mask_handle, shape_game
from apps.catalog.pricing import money

from . import constants as C


def _json(data):
    return json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')


@require_POST
def set_currency(request):
    code = request.POST.get('currency', 'COP')
    request.session['currency'] = code
    return redirect(request.META.get('HTTP_REFERER', '/'))


@require_POST
def set_price_mode(request):
    mode = request.POST.get('mode', 'Primaria')
    if mode in ('Primaria', 'Secundaria'):
        request.session['price_mode'] = mode
    return redirect(request.META.get('HTTP_REFERER', '/'))


def _currency(request):
    return request.session.get('currency', 'COP')


def _mode_currency(request):
    return request.session.get('price_mode', 'Primaria'), _currency(request)


def _sales_rank():
    """juego_id → unidades vendidas (pedidos aprobados)."""
    from apps.orders.models import ItemPedido
    rows = (ItemPedido.objects.filter(pedido__pago_estado='aprobado', juego__isnull=False)
            .values('juego_id').annotate(units=Sum('cantidad')))
    return {r['juego_id']: r['units'] or 0 for r in rows}


def _ranked(games):
    """Más vendidos primero; a igual venta, el de mayor precio (primaria)."""
    rank = _sales_rank()
    return sorted(games, key=lambda g: (-rank.get(g.pk, 0), -g.price_primary))


def _active_games():
    """Juegos activos desde la caché del catálogo (lista compartida: no mutar)."""
    return snapshot.active_games()


def _plat_match(game_plat, plat):
    return plat == 'Todos' or plat in game_plat


def _faq():
    from .context_processors import _countries
    names = [c['name'] for c in _countries('COP')]
    text = (', '.join(names[:-1]) + ' y ' + names[-1]) if len(names) > 1 else ''.join(names)
    return [{'q': f['q'], 'a': f['a'].replace('{countries}', text)} for f in C.FAQ]


# ---------------------------------------------------------------- home

HOME_RAIL = 12  # juegos del riel de ofertas del home (se repite para el loop)

def home(request):
    from apps.catalog.models import GiftCard, HeroVideo, PlusPlan, SiteSettings, Testimonial

    currency = _currency(request)
    games = _active_games()
    shaped = snapshot.shaped_games(currency)

    slides = []
    for hv in HeroVideo.objects.filter(active=True, juego__active=True).select_related('juego', 'juego__cover').order_by('order', 'id'):
        g = shaped.get(hv.juego_id)
        if not g:
            continue
        slides.append({**_slide(g), 'video': hv.video.url, 'image': hv.poster.url if hv.poster else g['cover_url']})
    if not slides:
        feat = [shaped[g.pk] for g in games if g.featured][:3]
        if len(feat) < 3:
            extra = [shaped[g.pk] for g in sorted(games, key=lambda g: -g.discount_percent) if not g.featured]
            feat += extra[:3 - len(feat)]
        slides = [{**_slide(g), 'video': '', 'image': g['cover_url']} for g in feat]

    ranked = _ranked(games)
    deals = [shaped[g.pk] for g in sorted(games, key=lambda g: -g.discount_percent) if g.discount_percent > 0][:HOME_RAIL]
    if not deals:
        deals = [shaped[g.pk] for g in ranked[:10]]

    cf = []
    for i, g in enumerate(ranked[:8]):
        s = shaped[g.pk]
        cf.append({'rank': i + 1, 'title': s['title'], 'plat': s['plat'], 'from': s['from'], 'url': s['url'],
                   'cover': s['cover_bg'], 'disc': s['disc'], 'initials': s['initials'], 'hasCover': s['has_cover']})

    top = {p: [shaped[g.pk] for g in ranked if _plat_match(g.platform, p)][:8] for p in ('Todos', 'PS5', 'PS4')}

    cheapest_plus = PlusPlan.objects.order_by('price').first()
    gifts = list(GiftCard.objects.order_by('denomination'))
    gift_desc = (f'De USD {gifts[0].denomination} a USD {gifts[-1].denomination}, región USA' if gifts
                 else 'Saldo para tu cuenta PSN')

    from .context_processors import genre_count
    genre_tiles = []
    for i, gn in enumerate(C.GENRES):
        n = genre_count(games, gn)
        if n:
            genre_tiles.append({'label': gn, 'count': f'{n} juegos', 'color': C.GENRE_COLORS[len(genre_tiles) % 4]})

    testimonials = [{'name': t.name, 'text': t.text} for t in Testimonial.objects.filter(active=True)] or C.REVIEWS_FALLBACK
    testimonials = [{'handle': mask_handle(t['name']), 'text': t['text']} for t in testimonials]
    settings_row = SiteSettings.load()

    ctx = {
        'slides': slides,
        'slide0': slides[0] if slides else None,
        'slides_json': _json(slides),
        'deals': deals,
        'coverflow': cf,
        'cf0': cf[0] if cf else None,
        'cf_json': _json(cf),
        'top': top['Todos'],
        'top_ps5': top['PS5'],
        'top_ps4': top['PS4'],
        'cats': [
            {'kicker': 'Suscripción', 'title': 'PS Plus', 'desc': 'Essential, Extra y Deluxe' + (f' · desde {money(cheapest_plus.price, currency)}' if cheapest_plus else ''), 'bar': '#FC3C00', 'url': reverse('store:plus')},
            {'kicker': 'Saldo PSN', 'title': 'Gift cards', 'desc': gift_desc, 'bar': '#FC8B01', 'url': reverse('store:giftcards')},
            {'kicker': 'Ahorra más', 'title': 'Combos', 'desc': '2 o 3 juegos en una sola compra', 'bar': '#FCC602', 'url': reverse('store:combos')},
        ],
        'stats': [
            {'n': str(len(games)), 'pre': '', 'v': f'{len(games):,}'.replace(',', '.'), 'l': 'títulos en catálogo'},
            {'n': '50000', 'pre': '+', 'v': '+50.000', 'l': 'entregas exitosas'},
            {'n': '1', 'pre': '', 'v': '1 año', 'l': 'de garantía'},
            {'n': '', 'pre': '', 'v': '5–15 min', 'l': 'de entrega'},
            {'n': '5', 'pre': '+', 'v': '+5 años', 'l': 'de experiencia'},
        ],
        'genre_tiles': genre_tiles,
        'steps': C.STEPS,
        'reviews': testimonials,
        'home_faqs': _faq()[:5],
        'review_count': f'{settings_row.review_count:,}'.replace(',', '.'),
        'review_rating': f'{settings_row.review_rating}'.replace('.', ','),
    }
    return render(request, 'store/home.html', ctx)


def _slide(g):
    return {'title': g['title'], 'plat': g['plat'], 'from': g['from'], 'disc': g['disc'], 'url': g['url']}


def search_api(request):
    q = request.GET.get('q', '').strip().lower()
    if len(q) < 2:
        return JsonResponse({'results': [], 'total': 0})
    currency = _currency(request)
    hits = [g for g in _active_games() if q in g.title.lower()]
    shaped = snapshot.shaped_games(currency)
    results = []
    for g in hits[:8]:
        s = shaped[g.pk]
        results.append({'title': s['title'], 'plat': s['plat'], 'from': s['from'], 'url': s['url'], 'cover': s['cover_bg']})
    return JsonResponse({'results': results, 'total': len(hits)})


# ------------------------------------------------------------- catálogo

CATALOG_PAGE = 48  # tarjetas por tanda (el resto se agrega al hacer scroll)


def _catalog_order():
    """Orden base ("Relevancia"): destacados primero y luego por título."""
    return snapshot.cached('catalog_order', lambda: sorted(_active_games(), key=lambda x: (not x.featured, x.title.lower())))


def _catalog_genres():
    from .context_processors import genre_count
    return snapshot.cached('catalog_genres', lambda: ['Todos'] + [gn for gn in C.GENRES if genre_count(_active_games(), gn)])


def _catalog_ctx(request, force_deals=False):
    """Catálogo y Ofertas comparten pantalla (en el diseño Ofertas es el
    catálogo con el filtro "Solo ofertas"). El servidor pinta solo la primera
    tanda de tarjetas según el estado de la URL; el navegador descarga el
    catálogo completo como JSON cacheable (`catalog_data`) y filtra, ordena y
    agrega tandas al hacer scroll sin volver al servidor
    (static/js/ganga-store.js). Sin JavaScript, "Ver más juegos" pagina con
    ?page=N."""
    currency = _currency(request)
    g = request.GET
    plat = g.get('platform', 'Todos')
    if plat not in ('Todos', 'PS5', 'PS4'):
        plat = 'Todos'
    genre = g.get('genre', 'Todos')
    only_deals = force_deals or g.get('deals') == '1'
    if only_deals:
        genre = 'Todos'
    sort = g.get('sort', 'Relevancia')
    if sort not in C.SORTS:
        sort = 'Relevancia'
    query = g.get('q', '').strip()
    try:
        page = max(1, min(int(g.get('page', 1)), 1000))
    except ValueError:
        page = 1

    genres = _catalog_genres()
    if genre not in genres:
        genre = 'Todos'

    shaped = snapshot.shaped_games(currency)
    q, genre_l = query.lower(), genre.lower()
    items = [shaped[x.pk] for x in _catalog_order()
             if _plat_match(x.platform, plat)
             and (genre == 'Todos' or genre_l in x.genre.lower())
             and (not only_deals or x.discount_percent > 0)
             and (not q or q in x.title.lower())]
    if sort == 'Menor precio':
        items.sort(key=lambda s: s['sec_cop'])
    elif sort == 'Mayor descuento':
        items.sort(key=lambda s: -s['disc_pct'])
    shown = items[:CATALOG_PAGE * page]

    more_url = ''
    if len(shown) < len(items):
        params = g.copy()
        params['page'] = page + 1
        more_url = '?' + params.urlencode()

    return {
        'games': shown,
        'result_count': len(items),
        'more_url': more_url,
        'catalog_page': CATALOG_PAGE,
        'data_url': f"{reverse('store:catalog_data')}?cur={currency}&v={snapshot.version()}",
        'catalog_title': 'Ofertas' if only_deals else 'Catálogo',
        'f_plat': plat, 'f_genre': genre, 'f_sort': sort, 'f_deals': only_deals, 'f_query': query,
        'plats': ['Todos', 'PS5', 'PS4'],
        'genres': genres,
        'sorts': C.SORTS,
    }


def catalog(request):
    return render(request, 'store/catalog.html', _catalog_ctx(request))


def deals(request):
    return render(request, 'store/catalog.html', _catalog_ctx(request, force_deals=True))


def catalog_data(request):
    """Catálogo completo en JSON compacto para filtrar en el navegador. La URL
    lleva la versión del catálogo y la divisa, así que el navegador la cachea;
    cuando algo cambia, la página pide una URL nueva."""
    from .context_processors import _countries

    currency = request.GET.get('cur', 'COP')
    if currency not in {c['code'] for c in _countries(currency)}:
        currency = 'COP'

    def build():
        shaped = snapshot.shaped_games(currency)
        rows = []
        for x in _catalog_order():
            s = shaped[x.pk]
            row = {'u': s['url'], 't': s['title'], 'p': s['plat'], 'g': x.genre.lower(),
                   'a': s['prim'], 'b': s['sec'], 's': s['sec_cop'], 'dp': s['disc_pct']}
            if s['has_cover']:
                row['c'] = s['cover_url']
            else:
                row['bg'], row['i'] = s['cover_bg'], s['initials']
            rows.append(row)
        return json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode('utf-8')

    body = snapshot.cached(('catalog_json', currency), build)
    # nginx no comprime JSON: se envía ya comprimido (y comprimido una sola vez por versión).
    if 'gzip' in request.headers.get('Accept-Encoding', ''):
        response = HttpResponse(snapshot.cached(('catalog_json_gz', currency), lambda: gzip.compress(body, 6)),
                                content_type='application/json')
        response['Content-Encoding'] = 'gzip'
    else:
        response = HttpResponse(body, content_type='application/json')
    response['Vary'] = 'Accept-Encoding'
    response['Cache-Control'] = 'public, max-age=86400'
    return response


# --------------------------------------------------------------- detalle

def detail(request, slug):
    from apps.catalog.models import SiteEvent

    currency = _currency(request)
    juego = get_object_or_404(Juego.objects.select_related('cover'), slug=slug, active=True)
    game = shape_game(juego, currency=currency)
    SiteEvent.objects.create(kind='ficha')

    others = [x for x in _active_games() if x.pk != juego.pk]
    related = [x for x in others if (x.genre == juego.genre or x.platform == juego.platform)][:6]
    if len(related) < 6:
        related += [x for x in others if x not in related][:6 - len(related)]
    shaped = snapshot.shaped_games(currency)

    ctx = {
        'game': game,
        'accounts': [
            {'id': 'primaria', 'name': 'Primaria', 'price': game['prim'], 'sum': 'Juegas desde tu propio usuario, con o sin internet.', 'tag': 'Más completa', 'tag_bg': '#FCC602'},
            {'id': 'secundaria', 'name': 'Secundaria', 'price': game['sec'], 'sum': 'Juegas desde el usuario que te entregamos, siempre conectado.', 'tag': f"Ahorras {game['savings']}", 'tag_bg': '#FC8B01'},
        ],
        'compare': C.COMPARE,
        'related': [shaped[x.pk] for x in related if x.pk in shaped],
    }
    return render(request, 'store/detail.html', ctx)


# --------------------------------------------------------------- carrito

def cart(request):
    from apps.catalog.models import SiteSettings
    from apps.orders.cart import Cart
    from apps.orders.payments import apply_account_credit, apply_coupon_code, apply_referral_code, cart_lines

    from .whatsapp import wa_link

    currency = _currency(request)
    session_cart = Cart(request)
    lines = cart_lines(list(session_cart))
    if len(lines) != len(session_cart.items):
        session_cart.items = [l['entry'] for l in lines]
        session_cart.save()

    items = []
    wa_lines = []
    for i, l in enumerate(lines):
        qty = l['cantidad']
        total = l['precio_cop'] * qty
        items.append({
            'index': i, 'title': l['titulo'], 'sub': l['sub'] + (f' · x{qty}' if qty > 1 else ''),
            'price': money(total, currency), 'cover_bg': l['cover_bg'], 'url': l['url'],
        })
        wa_lines.append(f"- {l['titulo']} ({l['sub']}) x{qty}: {money(total, currency)}")

    subtotal_cop = sum(l['precio_cop'] * l['cantidad'] for l in lines)
    settings_row = SiteSettings.load()
    referral_code, after_ref = apply_referral_code(request, subtotal_cop)
    coupon_code, after_coupon = apply_coupon_code(request, after_ref)
    coupon_disc = after_ref - after_coupon
    credit_used, total_cop = apply_account_credit(request, after_coupon)

    credit_available = int(request.user.credit or 0) if request.user.is_authenticated else 0

    text = 'Hola, quiero finalizar este pedido:\n' + '\n'.join(wa_lines)
    if referral_code:
        text += f'\nCódigo de referido: {referral_code}'
    if coupon_code:
        text += f'\nCupón: {coupon_code}'
    if credit_used:
        text += f'\nSaldo a favor usado: {money(credit_used, currency)}'
    text += f'\nTotal: {money(total_cop, currency)}'

    methods = []
    if settings_row.mercadopago_enabled:
        methods.append({'id': 'mp', 'name': 'Mercado Pago', 'desc': 'Tarjeta, PSE, Nequi o Efecty', 'label': 'Pagar con Mercado Pago', 'action': reverse('orders:checkout_mercadopago')})
    if settings_row.paypal_enabled:
        methods.append({'id': 'pp', 'name': 'PayPal', 'desc': 'Pago internacional en dólares', 'label': 'Pagar con PayPal', 'action': reverse('orders:checkout_paypal')})
    methods.append({'id': 'wa', 'name': 'WhatsApp', 'desc': 'Coordina el pago con un asesor', 'label': 'Continuar por WhatsApp', 'action': wa_link(text)})

    cart_msgs = [m for m in messages.get_messages(request) if 'cart' in m.tags]
    ref_msgs = [m for m in cart_msgs if 'ref' in m.tags.split()]
    coupon_msgs = [m for m in cart_msgs if 'ref' not in m.tags.split()]
    coupon_msg = coupon_msgs[-1] if coupon_msgs else None
    ref_msg = ref_msgs[-1] if ref_msgs else None

    ctx = {
        'items': items,
        'cart_empty': not items,
        'item_count': len(session_cart),
        'subtotal': money(subtotal_cop, currency),
        'coupon_code': coupon_code,
        'coupon_disc': money(coupon_disc, currency) if coupon_disc else '',
        'referral_enabled': settings_row.referral_enabled,
        'referral_code': referral_code,
        'credit_on': bool(request.session.get('use_credit')) and credit_available > 0,
        'credit_available': credit_available > 0,
        'credit_amount': money(credit_available, currency, allow_free=False),
        'credit_used': money(credit_used, currency) if credit_used else '',
        'total': money(total_cop, currency, allow_free=False),
        'total_cop': total_cop,
        'methods': methods,
        'coupon_msg': coupon_msg.message if coupon_msg else '',
        'coupon_msg_ok': bool(coupon_msg and coupon_msg.level_tag != 'error'),
        'coupon_msg_error': bool(coupon_msg and coupon_msg.level_tag == 'error'),
        'ref_msg': ref_msg.message if ref_msg else '',
        'ref_msg_ok': bool(ref_msg and ref_msg.level_tag != 'error'),
    }
    return render(request, 'store/cart.html', ctx)


# ---------------------------------------------------- combos / plus / gift

def combos(request):
    from apps.catalog.models import Combo
    from apps.catalog.presentation import cover_background

    currency = _currency(request)
    rows = []
    for c in Combo.objects.all().prefetch_related('games__cover'):
        games = list(c.games.all())
        if not games:
            continue
        sep = sum(g.price_primary for g in games)
        pct = round((1 - c.price_primary / sep) * 100) if sep else 0
        rows.append({
            'pk': c.pk, 'name': c.title,
            'covers': [cover_background(g) for g in games[:3]],
            'list': ' + '.join(g.title for g in games),
            'sep': money(sep, currency), 'price': money(c.price_primary, currency),
            'save': f'-{pct}%' if pct > 0 else '',
        })
    return render(request, 'store/combos.html', {'combos': rows})


def _perks(body):
    body = (body or '').strip()
    if '\n' in body:
        parts = [p.strip(' .•-') for p in body.splitlines()]
    else:
        parts = re.split(r',\s*|\s+y\s+|\s+más\s+', body.rstrip('.'))
    out = []
    for p in parts:
        p = re.sub(r'^(el|la|los|las)\s+', '', p.strip(), flags=re.I)
        if p:
            out.append(p[0].upper() + p[1:])
    return out


def plus(request):
    from apps.catalog.models import PlusPlan, TierInfo

    currency = _currency(request)
    platforms = sorted(set(PlusPlan.objects.values_list('platform', flat=True)), reverse=True)
    platform = request.GET.get('platform', 'PS5')
    if platform not in platforms:
        platform = platforms[0] if platforms else 'PS5'

    plans = {}
    months_set = set()
    for p in PlusPlan.objects.filter(platform=platform):
        months_set.add(p.months)
        plans.setdefault(p.tier, {})[str(p.months)] = {
            'id': p.pk, 'price': money(p.price, currency),
            'per': 'Pago mensual' if p.months == 1 else f'≈ {money(round(p.price / p.months), currency)} por mes',
        }
    months = sorted(months_set)
    default_months = 12 if 12 in months else (months[-1] if months else 1)

    tiers = []
    default_tier = None
    for info in TierInfo.objects.all().order_by('id'):
        if info.tier not in plans:
            continue
        tiers.append({'tier': info.tier, 'tag': info.label, 'perks': _perks(info.body), 'plans': plans[info.tier]})
        if info.recommended and not default_tier:
            default_tier = info.tier
    for t in tiers:
        plan = t['plans'].get(str(default_months)) or next(iter(t['plans'].values()))
        t['price'], t['per'] = plan['price'], plan['per']
    if not default_tier and tiers:
        default_tier = tiers[min(1, len(tiers) - 1)]['tier']

    sel = next((t for t in tiers if t['tier'] == default_tier), None)
    sel_plan = sel['plans'].get(str(default_months)) if sel else None
    return render(request, 'store/plus.html', {
        'tiers': tiers,
        'durations': [{'m': m, 'label': '1 mes' if m == 1 else f'{m} meses'} for m in months],
        'sel_tier': default_tier, 'sel_months': default_months,
        'sel_price': sel_plan['price'] if sel_plan else '',
        'sel_id': sel_plan['id'] if sel_plan else '',
        'plans_json': _json(plans),
        'platform': platform,
        'platforms': platforms if len(platforms) > 1 else [],
    })


def giftcards(request):
    from apps.catalog.models import GiftCard

    currency = _currency(request)
    cards = list(GiftCard.objects.all().order_by('denomination'))
    rows = [{'pk': g.pk, 'amt': g.denomination, 'price': money(g.price, currency), 'art': GIFT_ARTS[i % len(GIFT_ARTS)]}
            for i, g in enumerate(cards)]
    sel = next((r for r in rows if r['amt'] == 25), None) or (rows[len(rows) // 2] if rows else None)
    return render(request, 'store/giftcards.html', {'gifts': rows, 'sel': sel, 'gift_steps': C.GIFT_STEPS})


# ------------------------------------------------------- ayuda / legales

def help_view(request):
    from .whatsapp import wa_link

    issues = [{**h, 'link': wa_link(h['msg'], 'soporte')} for h in C.HELP_ISSUES]
    key = request.GET.get('issue', issues[0]['key'])
    sel = next((h for h in issues if h['key'] == key), issues[0])
    return render(request, 'store/help.html', {
        'issues': issues, 'sel': sel, 'issues_json': _json({h['key']: {'msg': h['msg'], 'link': h['link']} for h in issues}),
        'faqs': _faq(),
    })


def _legal(request, tab):
    sections = [{'n': f'{i + 1:02d}', 'title': t, 'body': body} for i, (t, body) in enumerate(C.LEGAL_T if tab == 'terminos' else C.LEGAL_P)]
    return render(request, 'store/legal.html', {
        'tab': tab,
        'legal_title': 'Términos y condiciones' if tab == 'terminos' else 'Política de privacidad',
        'sections': sections,
        'updated': C.LEGAL_UPDATED,
    })


def terms_view(request):
    return _legal(request, 'terminos')


def privacy_view(request):
    return _legal(request, 'privacidad')


# ------------------------------------------------------------ autenticación

def _current_country(request):
    from apps.catalog.models import Divisa
    code = _currency(request)
    d = Divisa.objects.filter(codigo=code).first()
    return (d.pais if d else 'Colombia'), C.DIALS.get(code, '+57')


def _format_whatsapp(phone_raw, dial):
    """'+<indicativo> <número agrupado>' (ej. '+57 311 482 9033')."""
    code = dial.lstrip('+')
    digits = re.sub(r'\D', '', phone_raw or '')
    if code and digits.startswith(code) and len(digits) > 10:
        digits = digits[len(code):]
    digits = digits.lstrip('0')
    if not digits:
        return ''
    groups = []
    if len(digits) > 4:
        groups.insert(0, digits[-4:])
        digits = digits[:-4]
    else:
        groups.insert(0, digits)
        digits = ''
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    if digits:
        groups.insert(0, digits)
    return f'+{code} ' + ' '.join(groups) if code else ' '.join(groups)


def auth_view(request):
    from django.contrib.auth import authenticate, get_user_model, login
    from django.utils.http import url_has_allowed_host_and_scheme

    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = ''
    target = next_url or 'store:account'
    if request.user.is_authenticated:
        return redirect(target)

    tab = request.GET.get('tab', 'login')
    if tab not in ('login', 'signup'):
        tab = 'login'
    error = None
    values = {}
    Usuario = get_user_model()
    country, dial = _current_country(request)

    if request.method == 'POST':
        tab = request.POST.get('tab', tab)
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        values = {'email': email, 'nombre': request.POST.get('nombre', ''), 'phone': request.POST.get('phone', '')}
        if tab == 'login':
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect(target)
            error = 'Correo o contraseña incorrectos.'
        else:
            nombre = request.POST.get('nombre', '').strip()
            phone = request.POST.get('phone', '').strip()
            if not (nombre and email and password):
                error = 'Completa nombre, correo y contraseña.'
            elif len(password) < 6:
                error = 'La contraseña debe tener al menos 6 caracteres.'
            elif Usuario.objects.filter(email=email).exists():
                error = 'Ya existe una cuenta con ese correo.'
            else:
                user = Usuario.objects.create_user(
                    email=email, password=password, nombre=nombre,
                    whatsapp=_format_whatsapp(phone, dial), pais=country, role='cliente',
                )
                from apps.accounts.models import Referido
                Referido.get_or_create_for(user)
                login(request, user)
                from .pixel import queue_pixel_event
                queue_pixel_event(request, 'CompleteRegistration', {'content_name': 'signup', 'status': True})
                return redirect(target)

    return render(request, 'store/auth.html', {
        'tab': tab, 'next': next_url, 'error': error, 'values': values, 'dial': dial,
    })


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('store:home')


@require_POST
def wishlist_toggle(request, pk):
    from apps.accounts.models import Wishlist

    if not request.user.is_authenticated:
        return redirect('store:auth')
    juego = get_object_or_404(Juego, pk=pk)
    existing = Wishlist.objects.filter(usuario=request.user, juego=juego).first()
    if existing:
        existing.delete()
    else:
        Wishlist.objects.create(usuario=request.user, juego=juego)
    return redirect(request.META.get('HTTP_REFERER', 'store:catalog'))


@require_POST
def redeem_saldo_codigo(request):
    from apps.catalog.models import SaldoCodigo
    from apps.orders.models import MovimientoCredito

    if not request.user.is_authenticated:
        return redirect('store:auth')
    code = request.POST.get('code', '').strip()
    saldo = SaldoCodigo.objects.filter(codigo__iexact=code).first()
    if not saldo:
        messages.error(request, 'Ese código no existe.', extra_tags='cuenta')
    elif saldo.estado != 'Activo':
        messages.error(request, 'Ese código ya no está disponible.', extra_tags='cuenta')
    else:
        saldo.usos_actuales += 1
        saldo.save(update_fields=['usos_actuales'])
        user = request.user
        user.credit += saldo.monto
        user.save(update_fields=['credit'])
        MovimientoCredito.objects.create(usuario=user, monto=saldo.monto, concepto=f'Código de saldo canjeado — {saldo.codigo}')
        messages.info(request, f'¡Listo! Se acreditaron {money(saldo.monto, _currency(request))} a tu cuenta.', extra_tags='cuenta')
    return redirect('store:account')


# ------------------------------------------------------------- mi cuenta

def _order_status(p):
    if p.estado == 'Entregado':
        return 'Entregado', '#25D366'
    if p.pago_estado in ('rechazado', 'cancelado'):
        return 'Pago ' + p.get_pago_estado_display().lower(), '#A9B8D6'
    if p.pago_estado == 'pendiente' and p.metodo_pago != 'whatsapp':
        return 'Pendiente de pago', '#FCC602'
    return 'En proceso', '#FCC602'


MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def account(request):
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from apps.accounts.models import Referido
    from apps.orders.models import Pedido

    from .context_processors import _countries
    from .whatsapp import wa_link

    if not request.user.is_authenticated:
        return redirect(f"{reverse('store:auth')}?next={reverse('store:account')}")

    user = request.user
    currency = _currency(request)
    tab = request.GET.get('tab', 'pedidos')
    if tab not in ('pedidos', 'datos'):
        tab = 'pedidos'
    countries = _countries(currency)
    profile_error = None

    if request.method == 'POST' and request.POST.get('action') == 'save_profile':
        tab = 'datos'
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip().lower()
        whatsapp = request.POST.get('whatsapp', '').strip()
        code = request.POST.get('country', '')
        country = next((c for c in countries if c['code'] == code), None)
        if not nombre or not email:
            profile_error = 'El nombre y el correo son obligatorios.'
        elif get_user_model().objects.filter(email=email).exclude(pk=user.pk).exists():
            profile_error = 'Ese correo ya está registrado en otra cuenta.'
        else:
            user.nombre, user.email, user.whatsapp = nombre, email, whatsapp
            if country:
                user.pais = country['name']
                request.session['currency'] = country['code']
            user.save(update_fields=['nombre', 'email', 'whatsapp', 'pais'])
            messages.success(request, 'Cambios guardados.', extra_tags='cuenta')
            return redirect(f"{reverse('store:account')}?tab=datos")

    orders = []
    for p in Pedido.objects.filter(usuario=user).prefetch_related('items__juego').order_by('-fecha'):
        items = list(p.items.all())
        first = items[0] if items else None
        title = first.titulo if first else 'Pedido'
        if len(items) > 1:
            title += f' + {len(items) - 1} más'
        if first and first.juego:
            sub = f'{first.juego.platform} · Cuenta {first.cuenta}' if first.cuenta else first.juego.platform
        elif first and first.titulo.startswith('PlayStation Plus'):
            sub = 'Suscripción'
        else:
            sub = 'Código digital' if first and 'Gift card' in first.titulo else ''
        st, st_bg = _order_status(p)
        fecha = timezone.localtime(p.fecha)
        creds = [{'title': i.titulo, 'text': i.credenciales_entregadas} for i in items if i.credenciales_entregadas]
        orders.append({
            'id': p.ref.lstrip('#'), 'date': f'{fecha.day} {MESES[fecha.month - 1]} {fecha.year}',
            'title': title, 'sub': sub, 'total': money(p.total, currency, allow_free=False),
            'st': st, 'st_bg': st_bg, 'delivered': p.estado == 'Entregado', 'creds': creds,
            'wa_link': wa_link(f'Hola, quiero consultar el estado de mi pedido {p.ref} ({title}).', 'soporte'),
        })

    referido, _ = Referido.get_or_create_for(user)
    cur = next((c for c in countries if c['name'] == user.pais), None) or next((c for c in countries if c['on']), None)
    acc_msgs = [m for m in messages.get_messages(request) if 'cuenta' in m.tags]
    return render(request, 'store/account.html', {
        'tab': tab,
        'orders': orders,
        'balance': money(user.credit or 0, currency, allow_free=False),
        'ref_code': referido.codigo,
        'acc_country': cur,
        'countries': countries,
        'profile_error': profile_error,
        'acc_msg': acc_msgs[-1].message if acc_msgs else '',
    })
