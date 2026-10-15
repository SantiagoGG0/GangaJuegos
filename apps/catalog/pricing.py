"""Conversión y formato de precios.

Todos los precios se cargan en COP. Cada divisa guarda en `Divisa.tasa`
cuántos COP vale 1 unidad de esa moneda (ej. USD 3436 → 1 USD = 3.436 COP),
editable desde el panel (pestaña Divisas). VES es especial: su `tasa` es la
tasa BCV en Bs por euro y el precio se arma en USD + un recargo fijo.

El formato (símbolo, decimales y redondeo) sigue el rediseño de Ganga
Juegos: `$ 139.900`, `US$ 34,15`, `AR$ 60.040`, `S/ 138,75`, `MX$ 713`,
`CLP$ 37.540`, `Gs 297.100`.
"""
from decimal import ROUND_HALF_UP, Decimal

VES_BCV_EUR = Decimal('947.3')
VES_MARKUP_USD = Decimal('3')

# código → (símbolo, decimales, paso de redondeo, etiqueta del redondeo)
CURRENCY_DISPLAY = {
    'COP': ('$', 0, Decimal('100'), 'Centena'),
    'USD': ('US$', 2, Decimal('0.01'), 'Centavo'),
    'USDEC': ('US$', 2, Decimal('0.01'), 'Centavo'),
    'MXN': ('MX$', 0, Decimal('1'), 'Unidad'),
    'ARS': ('AR$', 0, Decimal('10'), 'Decena'),
    'PEN': ('S/', 2, Decimal('0.01'), 'Céntimo'),
    'CLP': ('CLP$', 0, Decimal('10'), 'Decena'),
    'VES': ('Bs.', 0, Decimal('1'), 'Unidad'),
    'PYG': ('Gs', 0, Decimal('100'), 'Centena'),
}

# código ISO que se le muestra al cliente (USDEC es USD para Ecuador)
ISO_LABEL = {'USDEC': 'USD'}


def iso_label(code):
    return ISO_LABEL.get(code, code)


def _round_step(value, step):
    return (value / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step


def _fmt(value, symbol, decimals, step=None):
    if step:
        value = _round_step(value, step)
    q = Decimal(10) ** -decimals if decimals else Decimal(1)
    value = value.quantize(q, rounding=ROUND_HALF_UP)
    if decimals:
        text = f'{value:,.{decimals}f}'
    else:
        text = f'{int(value):,}'
    text = text.replace(',', '·').replace('.', ',').replace('·', '.')
    return f'{symbol} {text}'


_RATES = {'at': 0.0, 'rates': {}}


def _rates():
    """Tasas de todas las divisas, cacheadas 5 s en memoria: una página de
    catálogo formatea cientos de precios y no tiene sentido ir a la base de
    datos por cada uno. `clear_rates_cache()` se llama al guardar tasas."""
    import time

    from .models import Divisa
    now = time.monotonic()
    if now - _RATES['at'] > 5:
        _RATES['rates'] = {d.codigo: d.tasa for d in Divisa.objects.all()}
        _RATES['at'] = now
    return _RATES['rates']


def clear_rates_cache():
    _RATES['at'] = 0.0


def get_rate(cur):
    if cur == 'COP':
        return Decimal('1')
    return _rates().get(cur, Decimal('1'))


def ves_bcv():
    return _rates().get('VES') or VES_BCV_EUR


def ves_bs(cop):
    return (Decimal(cop) / get_rate('USD') + VES_MARKUP_USD) * ves_bcv()


def convert(cop, cur='COP'):
    """Valor numérico (Decimal) ya convertido a la moneda, sin formato."""
    cop = Decimal(cop)
    if cur == 'COP':
        return cop
    if cur == 'VES':
        return ves_bs(cop)
    rate = get_rate(cur)
    if not rate:
        return cop
    return cop / rate


def money(cop, cur='COP', allow_free=True):
    cop = Decimal(cop)
    if cop == 0 and allow_free:
        return 'Gratis'
    if cur not in CURRENCY_DISPLAY:
        cur = 'COP'
    symbol, decimals, step, _ = CURRENCY_DISPLAY[cur]
    if cur != 'COP' and cur != 'VES' and not get_rate(cur):
        return money(cop, 'COP', allow_free)
    return _fmt(convert(cop, cur), symbol, decimals, step)


def money_sum(cops, cur='COP'):
    if cur == 'VES':
        symbol, decimals, step, _ = CURRENCY_DISPLAY['VES']
        total = sum((ves_bs(c) for c in cops), Decimal(0))
        return _fmt(total, symbol, decimals, step)
    return money(sum(cops), cur)
