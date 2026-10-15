"""Panel de administración (diseño "Ganga Juegos Panel"): Resumen, Catálogo,
Ofertas, Cupones, Métricas, Divisas, Carátulas y Carga masiva, todo con
datos reales de la base. Cada pestaña es una vista protegida por el
AdminSite (`admin_view`)."""
import csv
import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.catalog.models import Cupon, Divisa, Juego
from apps.catalog.presentation import cover_background
from apps.catalog.pricing import CURRENCY_DISPLAY, clear_rates_cache, iso_label, money
from apps.orders.models import ItemPedido, Pedido
from apps.store import constants as C

MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

TABS = [
    ('resumen', 'Resumen', 'gsadmin:dashboard_resumen', 'Hoy'),
    ('catalogo', 'Catálogo', 'gsadmin:dashboard_catalogo', 'Productos'),
    ('ofertas', 'Ofertas', 'gsadmin:dashboard_ofertas', 'Precios'),
    ('cupones', 'Cupones', 'gsadmin:dashboard_cupones', 'Descuentos'),
    ('metricas', 'Métricas', 'gsadmin:dashboard_metricas', 'Rendimiento'),
    ('divisas', 'Divisas', 'gsadmin:dashboard_divisas', 'Monedas'),
    ('caratulas', 'Carátulas', 'gsadmin:covers_manager', 'Imágenes'),
    ('carga', 'Carga masiva', 'gsadmin:products_bulk', 'Importar'),
]

# estado → (etiqueta, fondo, texto) — paleta del diseño
ST_STYLE = {
    'Por entregar': ('#FFF0C2', '#7A4B00'),
    'Entregado': ('#D7F5E3', '#0B5D33'),
    'Pendiente de pago': ('#FFE1D6', '#9A2A00'),
    'Pago rechazado': ('#FFE1D6', '#9A2A00'),
    'Cancelado': ('#EFE8DD', '#4A5A78'),
}


def fecha_es(d):
    return f'{d.day} {MESES[d.month - 1]}'


def order_status(p):
    if p.estado == 'Entregado':
        return 'Entregado'
    if p.pago_estado == 'aprobado':
        return 'Por entregar'
    if p.pago_estado == 'pendiente':
        return 'Pendiente de pago'
    if p.pago_estado == 'rechazado':
        return 'Pago rechazado'
    return 'Cancelado'


def pending_deliveries():
    return Pedido.objects.filter(pago_estado='aprobado').exclude(estado='Entregado').count()


def missing_covers():
    return Juego.objects.filter(cover__isnull=True).count()


def country_flag(pais):
    return C.FLAGS.get(C.COUNTRY_TO_CURRENCY.get(pais, ''), '#CFC6B8')


def base_context(request, active):
    badges = {'resumen': pending_deliveries(), 'caratulas': missing_covers()}
    tab = next(t for t in TABS if t[0] == active)
    now = timezone.localtime()
    return {
        'tabs': [{'key': k, 'label': label, 'url': reverse(url), 'on': k == active, 'badge': badges.get(k, 0)}
                 for k, label, url, _ in TABS],
        'kicker': tab[3], 'title': tab[1],
        'today_label': f'{DIAS[now.weekday()]} {now.day} {MESES[now.month - 1]} {now.year}',
        'admin_who': request.user.email,
    }


def _seg(options, current, param, extra=''):
    return [{'label': label, 'on': str(value) == str(current), 'url': f'?{param}={value}{extra}'} for value, label in options]


# ---------------------------------------------------------------- Resumen

def tab_resumen(request):
    ctx = base_context(request, 'resumen')
    now = timezone.localtime()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    qs = (Pedido.objects.filter(Q(fecha__gte=today) | Q(pago_estado='aprobado', estado='En proceso'))
          .select_related('usuario').prefetch_related('items').order_by('-fecha'))
    rows = []
    for p in qs:
        st = order_status(p)
        items = list(p.items.all())
        first = items[0] if items else None
        product = (first.titulo if first else '—') + (f' + {len(items) - 1}' if len(items) > 1 else '')
        cuenta = first.cuenta.capitalize() if first and first.cuenta else '—'
        mins = int((now - timezone.localtime(p.fecha)).total_seconds() // 60)
        when = f'hace {mins} min' if mins < 60 else (f'hace {mins // 60} h' if mins < 1440 else fecha_es(timezone.localtime(p.fecha)))
        rows.append({
            'pk': p.pk, 'id': p.ref.lstrip('#'), 'when': when,
            'client': p.usuario.nombre or p.usuario.email, 'flag': country_flag(p.usuario.pais),
            'product': product, 'acc': cuenta, 'pay': p.get_metodo_pago_display(),
            'total': money(p.total, allow_free=False), 'st': st,
            'st_bg': ST_STYLE[st][0], 'st_fg': ST_STYLE[st][1], 'can_deliver': st == 'Por entregar',
        })

    f = request.GET.get('f', 'Todos')
    if f not in ('Todos', 'Por entregar', 'Entregado'):
        f = 'Todos'
    shown = [r for r in rows if f == 'Todos' or r['st'] == f]

    today_qs = Pedido.objects.filter(fecha__gte=today, pago_estado='aprobado').select_related('usuario')
    total = today_qs.aggregate(s=Sum('total'))['s'] or 0
    n_today = Pedido.objects.filter(fecha__gte=today).count()
    approved = today_qs.count()
    pending = pending_deliveries()
    countries = {p.usuario.pais for p in today_qs if p.usuario.pais}
    n_countries = Divisa.objects.count()

    ctx.update({
        'kpis': [
            {'label': 'Ventas de hoy', 'value': money(total, allow_free=False), 'note': f'{n_today} pedidos', 'bg': '#011E4F', 'fg': '#FCF8F3', 'border': '#011E4F'},
            {'label': 'Por entregar', 'value': str(pending), 'note': 'Entrégalos antes de 15 min', 'bg': '#FCC602' if pending else '#fff', 'fg': '#011E4F', 'border': '#FCC602' if pending else '#E6DED2'},
            {'label': 'Ticket promedio', 'value': money(total / approved if approved else 0, allow_free=False), 'note': 'Hoy', 'bg': '#fff', 'fg': '#011E4F', 'border': '#E6DED2'},
            {'label': 'Países con ventas', 'value': f'{len(countries)} de {n_countries}', 'note': 'Hoy', 'bg': '#fff', 'fg': '#011E4F', 'border': '#E6DED2'},
        ],
        'order_filters': _seg([('Todos', 'Todos'), ('Por entregar', 'Por entregar'), ('Entregado', 'Entregado')], f, 'f'),
        'orders': shown,
    })
    return render(request, 'panel/resumen.html', ctx)


@require_POST
def deliver_order(request, pk):
    p = get_object_or_404(Pedido, pk=pk)
    p.estado = 'Entregado'
    p.save(update_fields=['estado'])
    messages.success(request, f'Pedido {p.ref} marcado como entregado.')
    return redirect(request.META.get('HTTP_REFERER') or reverse('gsadmin:dashboard_resumen'))


def export_clientes_csv(request):
    Usuario = get_user_model()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clientes-gangajuegos.csv"'
    response.write('﻿')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['nombre', 'correo', 'whatsapp', 'pais', 'rol', 'alta'])
    for u in Usuario.objects.all().order_by('-date_joined'):
        writer.writerow([u.nombre, u.email, u.whatsapp, u.pais, u.role, u.date_joined.strftime('%Y-%m-%d')])
    return response


# --------------------------------------------------------------- Catálogo

def tab_catalogo(request):
    ctx = base_context(request, 'catalogo')
    q = request.GET.get('q', '').strip()
    plat = request.GET.get('plat', 'Todos')
    if plat not in ('Todos', 'PS5', 'PS4'):
        plat = 'Todos'
    qs = Juego.objects.all().select_related('cover').order_by('title')
    if q:
        qs = qs.filter(title__icontains=q)
    if plat != 'Todos':
        qs = qs.filter(platform__contains=plat)
    rows = [{
        'pk': g.pk, 'title': g.title, 'plat': g.platform, 'genre': g.genre, 'cover_bg': cover_background(g),
        'prim': money(g.price_primary, allow_free=False), 'sec': money(g.price_secondary, allow_free=False),
        'old': money(g.old_price_primary, allow_free=False) if g.old_price_primary else '—',
        'active': g.active, 'featured': g.featured, 'edit_url': reverse('gsadmin:catalog_juego_change', args=[g.pk]),
    } for g in qs]
    extra = f'&q={q}' if q else ''
    ctx.update({
        'q': q, 'plat_filters': _seg([('Todos', 'Todos'), ('PS5', 'PS5'), ('PS4', 'PS4')], plat, 'plat', extra),
        'rows': rows, 'count': len(rows), 'new_url': reverse('gsadmin:catalog_juego_add'),
        'total': Juego.objects.count(), 'delete_confirm': DELETE_ALL_CONFIRM,
    })
    return render(request, 'panel/catalogo.html', ctx)


@require_POST
def toggle_juego_active(request, pk):
    juego = get_object_or_404(Juego, pk=pk)
    juego.active = not juego.active
    juego.save(update_fields=['active'])
    return redirect(request.META.get('HTTP_REFERER') or reverse('gsadmin:dashboard_catalogo'))


DELETE_ALL_CONFIRM = 'ELIMINAR TODO'


def _back_to_catalog(request):
    return redirect(request.META.get('HTTP_REFERER') or reverse('gsadmin:dashboard_catalogo'))


def _delete_juegos(qs):
    """Borra los juegos y los archivos de sus carátulas y videos del hero (Django
    no borra los archivos al borrar el registro). Los pedidos se conservan: el
    ítem guarda el título y queda sin juego enlazado."""
    from apps.catalog.models import Cover, HeroVideo
    files = [c.image for c in Cover.objects.filter(juego__in=qs) if c.image]
    for hv in HeroVideo.objects.filter(juego__in=qs):
        files += [f for f in (hv.video, hv.poster) if f]
    with transaction.atomic():
        qs.delete()
    for f in files:
        try:
            f.storage.delete(f.name)
        except Exception:  # noqa: BLE001
            pass


@require_POST
def juego_delete(request, pk):
    juego = get_object_or_404(Juego, pk=pk)
    title = juego.title
    _delete_juegos(Juego.objects.filter(pk=pk))
    messages.success(request, f'Juego eliminado: {title}.')
    return _back_to_catalog(request)


BULK_ACTIONS = {
    'activar': ('activados', {'active': True}),
    'ocultar': ('ocultados', {'active': False}),
    'destacar': ('marcados como destacados', {'featured': True}),
    'quitar_destacado': ('sin destacar', {'featured': False}),
}


@require_POST
def catalog_bulk(request):
    ids = [int(i) for i in request.POST.getlist('ids') if i.isdigit()]
    action = request.POST.get('action', '')
    qs = Juego.objects.filter(pk__in=ids)
    count = qs.count()
    if not count:
        messages.error(request, 'Selecciona al menos un juego.')
    elif action == 'eliminar':
        _delete_juegos(qs)
        messages.success(request, f'{count} juego(s) eliminados.')
    elif action in BULK_ACTIONS:
        label, fields = BULK_ACTIONS[action]
        qs.update(**fields)
        from apps.catalog import snapshot
        snapshot.bump()
        messages.success(request, f'{count} juego(s) {label}.')
    else:
        messages.error(request, 'Elige una acción.')
    return _back_to_catalog(request)


@require_POST
def catalog_delete_all(request):
    if request.POST.get('confirm', '').strip().upper() != DELETE_ALL_CONFIRM:
        messages.error(request, f'Para eliminar todo el catálogo escribe exactamente "{DELETE_ALL_CONFIRM}".')
        return redirect('gsadmin:dashboard_catalogo')
    count = Juego.objects.count()
    _delete_juegos(Juego.objects.all())
    messages.success(request, f'Catálogo eliminado: {count} juego(s) borrados con sus carátulas.')
    return redirect('gsadmin:dashboard_catalogo')


# ---------------------------------------------------------------- Ofertas

def tab_ofertas(request):
    from apps.catalog.offers import expire_offers
    expire_offers(force=True)
    ctx = base_context(request, 'ofertas')
    offers = Juego.objects.filter(Q(old_price_primary__isnull=False) | Q(old_price_secondary__isnull=False)).select_related('cover').order_by('title')
    rows = [{
        'pk': g.pk, 'title': g.title, 'cover_bg': cover_background(g), 'pct': f'-{g.discount_percent}%',
        'price': money(g.price_primary, allow_free=False),
        'old': money(g.old_price_primary or g.price_primary, allow_free=False),
        'ends': fecha_es(g.oferta_termina) if g.oferta_termina else 'Sin fecha',
    } for g in offers]
    candidates = Juego.objects.filter(active=True, old_price_primary__isnull=True, old_price_secondary__isnull=True).order_by('title')
    ctx.update({
        'rows': rows,
        'candidates': [{'pk': g.pk, 'title': g.title, 'prim': g.price_primary} for g in candidates],
        'today': timezone.localdate().isoformat(),
    })
    return render(request, 'panel/ofertas.html', ctx)


@require_POST
def offer_create(request):
    from apps.catalog.offers import apply_offer
    juego = get_object_or_404(Juego, pk=request.POST.get('juego'))
    try:
        pct = int(request.POST.get('pct', 20))
    except ValueError:
        pct = 20
    ends = request.POST.get('ends') or None
    try:
        ends = datetime.date.fromisoformat(ends) if ends else None
    except ValueError:
        ends = None
    apply_offer(juego, pct, ends)
    messages.success(request, f'Oferta publicada: {juego.title} con {pct}% de descuento.')
    return redirect('gsadmin:dashboard_ofertas')


@require_POST
def offer_remove(request, pk):
    from apps.catalog.offers import remove_offer
    juego = get_object_or_404(Juego, pk=pk)
    remove_offer(juego)
    messages.success(request, f'Oferta retirada: {juego.title} volvió a su precio anterior.')
    return redirect('gsadmin:dashboard_ofertas')


# ---------------------------------------------------------------- Cupones

def tab_cupones(request):
    ctx = base_context(request, 'cupones')
    rows = []
    for c in Cupon.objects.all().order_by('-id'):
        pct = min(100, round(c.usos_actuales / c.usos_max * 100)) if c.usos_max else 0
        rows.append({
            'pk': c.pk, 'code': c.code, 'val': c.valor_display, 'usage': c.uso_display, 'pct_w': f'{pct}%',
            'ends': f'{c.vence.day} {MESES[c.vence.month - 1]} {c.vence.year}' if c.vence else 'Sin vencimiento',
            'on': c.activo, 'state': 'Agotado' if c.estado == 'Agotado' else ('Activo' if c.activo else 'Oculto'),
        })
    ctx['rows'] = rows
    ctx['form'] = request.session.pop('cupon_form', {'code': '', 'tipo': '%', 'valor': '15', 'max': ''})
    return render(request, 'panel/cupones.html', ctx)


@require_POST
def coupon_toggle(request, pk):
    c = get_object_or_404(Cupon, pk=pk)
    c.activo = not c.activo
    c.save(update_fields=['activo'])
    return redirect('gsadmin:dashboard_cupones')


@require_POST
def coupon_create(request):
    code = request.POST.get('code', '').strip().upper()
    tipo = 'porcentaje' if request.POST.get('tipo', '%') == '%' else 'monto_fijo'
    valor_raw = request.POST.get('valor', '').strip()
    max_raw = request.POST.get('max', '').strip()
    form = {'code': code, 'tipo': '%' if tipo == 'porcentaje' else '$', 'valor': valor_raw, 'max': max_raw}
    error = None
    try:
        valor = Decimal(valor_raw.replace('.', '').replace(',', '.')) if tipo == 'monto_fijo' else Decimal(valor_raw.replace(',', '.'))
    except InvalidOperation:
        valor = None
    if not code:
        error = 'Escribe el código del cupón.'
    elif Cupon.objects.filter(code__iexact=code).exists():
        error = f'Ya existe un cupón con el código {code}.'
    elif not valor or valor <= 0 or (tipo == 'porcentaje' and valor > 100):
        error = 'El valor debe ser un número mayor que 0 (y hasta 100 si es porcentaje).'
    elif max_raw and not max_raw.isdigit():
        error = 'El máximo de usos debe ser un número entero (o vacío para sin límite).'
    if error:
        messages.error(request, error)
        request.session['cupon_form'] = form
    else:
        Cupon.objects.create(code=code, tipo=tipo, valor=valor, usos_max=int(max_raw) if max_raw else None, vence=None, activo=True)
        messages.success(request, f'Cupón {code} creado.')
    return redirect('gsadmin:dashboard_cupones')


# --------------------------------------------------------------- Métricas

def tab_metricas(request):
    ctx = base_context(request, 'metricas')
    try:
        n = int(request.GET.get('p', 14))
    except ValueError:
        n = 14
    if n not in (7, 14, 30):
        n = 14
    now = timezone.localtime()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - datetime.timedelta(days=n - 1)
    approved = Pedido.objects.filter(pago_estado='aprobado', fecha__gte=start).select_related('usuario')

    vals = []
    for i in range(n):
        d0 = start + datetime.timedelta(days=i)
        s = approved.filter(fecha__gte=d0, fecha__lt=d0 + datetime.timedelta(days=1)).aggregate(s=Sum('total'))['s'] or 0
        vals.append(float(s) / 1_000_000)
    mx = max(vals) or 1
    total = sum(vals)
    grad = 'linear-gradient(0deg,#FC3C00,#FC8B01 60%,#FCC602)'

    def mfmt(v):
        return f'$ {v:.1f} M'.replace('.', ',')

    by_country = {}
    for p in approved:
        key = p.usuario.pais or 'Sin país'
        by_country[key] = by_country.get(key, 0) + float(p.total)
    tot_c = sum(by_country.values()) or 1
    countries = sorted(by_country.items(), key=lambda kv: -kv[1])
    top_pct = (countries[0][1] / tot_c * 100) if countries else 1

    items = ItemPedido.objects.filter(pedido__pago_estado='aprobado', pedido__fecha__gte=start)
    top = (items.filter(juego__isnull=False).values('juego_id', 'juego__title')
           .annotate(units=Sum('cantidad')).order_by('-units')[:5])
    juegos = {g.pk: g for g in Juego.objects.filter(pk__in=[t['juego_id'] for t in top]).select_related('cover')}
    prim = items.filter(cuenta='primaria').aggregate(s=Sum('cantidad'))['s'] or 0
    sec = items.filter(cuenta='secundaria').aggregate(s=Sum('cantidad'))['s'] or 0
    prim_pct = round(prim / (prim + sec) * 100) if (prim + sec) else 50

    ctx.update({
        'periods': _seg([(7, '7 días'), (14, '14 días'), (30, '30 días')], n, 'p'),
        'kpis': [
            {'label': 'Ingresos', 'value': mfmt(total)},
            {'label': 'Pedidos', 'value': str(approved.count())},
            {'label': 'Promedio diario', 'value': mfmt(total / n)},
        ],
        'bars': [{'h': f'{(v / mx * 100) if v else 1:.1f}%', 'bg': grad if i == n - 1 else '#2D5AA8', 'tip': mfmt(v)} for i, v in enumerate(vals)],
        'bar_gap': '3px' if n > 20 else '6px',
        'bar_start': f'Hace {n - 1} días',
        'by_country': [{'name': name, 'flag': country_flag(name), 'w': f'{v / tot_c * 100 / top_pct * 100:.0f}%', 'pct': f'{round(v / tot_c * 100)}%'} for name, v in countries],
        'top_games': [{'n': i + 1, 'title': t['juego__title'], 'cover_bg': cover_background(juegos[t['juego_id']]) if t['juego_id'] in juegos else '', 'units': f"{t['units']} ventas"} for i, t in enumerate(top)],
        'prim_pct': prim_pct, 'sec_pct': 100 - prim_pct,
    })
    return render(request, 'panel/metricas.html', ctx)


# ---------------------------------------------------------------- Divisas

DIVISA_ROWS = ['COP', 'USD', 'ARS', 'PEN', 'MXN', 'CLP', 'PYG', 'VES']


def _divisas():
    return {d.codigo: d for d in Divisa.objects.all()}


def tab_divisas(request):
    ctx = base_context(request, 'divisas')
    divs = _divisas()
    usd = divs.get('USD') or divs.get('USDEC')
    usd_cop = usd.tasa if usd else Decimal('4100')
    sample = Juego.objects.filter(active=True).order_by('-featured', 'title').first()
    sample_cop = sample.price_primary if sample else 100000

    def fmt_rate(v):
        v = Decimal(v)
        if v >= 100:
            return str(int(v.quantize(Decimal('1'))))
        s = f'{v:.2f}'.rstrip('0').rstrip('.')
        return s.replace('.', ',')

    rows = []
    for code in DIVISA_ROWS:
        members = [d for c, d in divs.items() if iso_label(c) == code] if code != 'VES' else [divs['VES']] if 'VES' in divs else []
        if code == 'COP':
            members = [divs['COP']] if 'COP' in divs else []
        if not members:
            continue
        countries = [{'name': d.pais, 'flag': C.FLAGS.get(d.codigo, '#CFC6B8')} for d in sorted(members, key=lambda d: C.COUNTRY_ORDER.index(d.codigo) if d.codigo in C.COUNTRY_ORDER else 99)]
        if code == 'COP':
            rate, editable, label = fmt_rate(usd_cop), True, '1 USD ='
        elif code == 'USD':
            rate, editable, label = '1', False, '1 USD ='
        elif code == 'VES':
            rate, editable, label = fmt_rate(members[0].tasa), True, '1 € (BCV) ='
        else:
            rate, editable, label = fmt_rate(usd_cop / members[0].tasa if members[0].tasa else 0), True, '1 USD ='
        disp = CURRENCY_DISPLAY.get(members[0].codigo, CURRENCY_DISPLAY['COP'])
        rows.append({
            'code': code, 'countries': countries, 'rate': rate, 'editable': editable, 'rate_label': label,
            'round': disp[3] + (' · +3 USD por línea' if code == 'VES' else ''),
            'example': money(sample_cop, members[0].codigo, allow_free=False),
            'updated': max(d.actualizado for d in members),
        })
    last = max((r['updated'] for r in rows), default=None)
    note = request.session.pop('rates_note', None)
    if not note and last:
        lt = timezone.localtime(last)
        note = f'Última actualización: {lt.day} {MESES[lt.month - 1]}, {lt:%H:%M}'
    ctx.update({
        'rows': rows,
        'sample_title': sample.title if sample else 'un juego',
        'sample_cop': money(sample_cop, allow_free=False),
        'rates_note': note,
    })
    return render(request, 'panel/divisas.html', ctx)


@require_POST
def save_rates(request):
    divs = _divisas()

    def num(code):
        import re
        raw = (request.POST.get(f'rate_{code}') or '').strip().replace(' ', '')
        if re.fullmatch(r'\d{1,3}(\.\d{3})+(,\d+)?', raw):  # 4.100 / 1.400,5 → separador de miles
            raw = raw.replace('.', '')
        raw = raw.replace(',', '.')
        try:
            v = Decimal(raw)
            return v if v > 0 else None
        except InvalidOperation:
            return None

    usd_cop = num('COP')
    errors = []
    if usd_cop:
        for c in ('USD', 'USDEC'):
            if c in divs:
                divs[c].tasa = usd_cop
                divs[c].save(update_fields=['tasa', 'actualizado'])
    else:
        errors.append('COP')
    usd_cop = usd_cop or (divs['USD'].tasa if 'USD' in divs else None)
    for code in ('ARS', 'PEN', 'MXN', 'CLP', 'PYG'):
        if code not in divs or f'rate_{code}' not in request.POST:
            continue
        v = num(code)
        if v and usd_cop:
            divs[code].tasa = (usd_cop / v).quantize(Decimal('0.0001'))
            divs[code].save(update_fields=['tasa', 'actualizado'])
        else:
            errors.append(code)
    if 'VES' in divs and 'rate_VES' in request.POST:
        v = num('VES')
        if v:
            divs['VES'].tasa = v
            divs['VES'].save(update_fields=['tasa', 'actualizado'])
        else:
            errors.append('VES')
    clear_rates_cache()
    if errors:
        request.session['rates_note'] = 'No se guardaron: ' + ', '.join(errors) + ' (valor inválido). El resto quedó actualizado.'
    else:
        request.session['rates_note'] = 'Tasas guardadas · los precios de la tienda ya se actualizaron'
    return redirect('gsadmin:dashboard_divisas')


# -------------------------------------------------------------- Carátulas

def tab_caratulas(request):
    ctx = base_context(request, 'caratulas')
    f = request.GET.get('f', 'Todas')
    games = Juego.objects.all().select_related('cover').order_by('title')
    n_missing = missing_covers()
    rows = []
    for g in games:
        has = hasattr(g, 'cover') and bool(g.cover.image)
        if f == 'Faltantes' and has:
            continue
        rows.append({
            'slug': g.slug, 'title': g.title, 'missing': not has,
            'bg': cover_background(g) if has else 'background:repeating-linear-gradient(135deg,#FFF3EC 0 8px,#FFE9DD 8px 16px)',
            'upload_url': reverse('gsadmin:covers_assign_one', args=[g.slug]),
        })
    ctx.update({
        'cover_filters': _seg([('Todas', 'Todas'), ('Faltantes', f'Sin carátula ({n_missing})')], f, 'f'),
        'rows': rows,
    })
    return render(request, 'panel/caratulas.html', ctx)

