"""Integración con Mercado Pago y PayPal.

Ambos proveedores se agregan como una OPCIÓN MÁS junto al cierre por
WhatsApp que ya existía — no lo reemplazan. El pedido (Pedido + ItemPedido)
se crea en el momento en que el cliente elige pagar en línea, con
`pago_estado='pendiente'`, y se marca `aprobado`/`rechazado` cuando el
proveedor confirma el pago (nunca confiando en lo que venga en la URL de
retorno sin verificarlo contra la API del proveedor con nuestro propio
access token/secret).
"""
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote

import mercadopago
import requests
from django.conf import settings
from django.urls import reverse

from apps.catalog.models import Combo, Juego, PlusPlan, SiteSettings
from apps.catalog.pricing import get_rate

from .cart import Cart
from .models import ItemPedido, MovimientoCredito, Pedido


def cart_lines(cart_items):
    """Resuelve las líneas del carrito de sesión contra la base de datos.

    Devuelve una lista de dicts con todo lo necesario tanto para pintar el
    carrito como para crear el pedido: título, juego (si aplica), precio
    unitario en COP según la cuenta elegida en esa línea, cantidad, cuenta,
    subtítulo y fondo de carátula. Las líneas cuyo producto ya no existe se
    omiten (y `valid_entries` permite limpiarlas de la sesión)."""
    from apps.catalog.models import GiftCard
    from apps.catalog.presentation import cover_background, GRAD, PLUS_ART, GIFT_ART

    lines = []
    for idx, entry in enumerate(cart_items):
        kind, pk, qty = entry['type'], entry['id'], entry.get('qty', 1)
        acc = entry.get('acc') or 'primaria'
        prim = acc == 'primaria'
        if kind == 'juego':
            juego = Juego.objects.filter(pk=pk, active=True).select_related('cover').first()
            if not juego:
                continue
            lines.append({
                'entry': entry, 'kind': kind, 'titulo': juego.title, 'juego': juego,
                'precio_cop': juego.price_primary if prim else juego.price_secondary,
                'cantidad': qty, 'cuenta': acc,
                'sub': f"{juego.platform} · Cuenta {acc}",
                'cover_bg': cover_background(juego), 'url': f'/juego/{juego.slug}/',
            })
        elif kind == 'combo':
            combo = Combo.objects.filter(pk=pk).prefetch_related('games').first()
            if not combo:
                continue
            n = combo.games.count()
            lines.append({
                'entry': entry, 'kind': kind, 'titulo': combo.title, 'juego': None,
                'precio_cop': combo.price_primary if prim else combo.price_secondary,
                'cantidad': qty, 'cuenta': acc,
                'sub': f'Combo · {n} juegos · {acc.capitalize()}',
                'cover_bg': f'background:{GRAD}', 'url': '/combos/',
            })
        elif kind == 'plan':
            plan = PlusPlan.objects.filter(pk=pk).first()
            if not plan:
                continue
            label = '1 mes' if plan.months == 1 else f'{plan.months} meses'
            lines.append({
                'entry': entry, 'kind': kind, 'titulo': f'PS Plus {plan.tier}', 'juego': None,
                'precio_cop': plan.price, 'cantidad': qty, 'cuenta': '',
                'sub': f'Suscripción · {label}', 'order_title': f'PlayStation Plus {plan.tier} ({label})',
                'cover_bg': f'background:{PLUS_ART}', 'url': '/plus/',
            })
        elif kind == 'gift':
            gift = GiftCard.objects.filter(pk=pk).first()
            if not gift:
                continue
            lines.append({
                'entry': entry, 'kind': kind, 'titulo': f'Gift card PSN USD {gift.denomination}', 'juego': None,
                'precio_cop': gift.price, 'cantidad': qty, 'cuenta': '',
                'sub': f'Código digital · {gift.region}',
                'cover_bg': f'background:{GIFT_ART}', 'url': '/tarjetas-regalo/',
            })
    return lines


def apply_referral_code(request, total_cop):
    """Valida el código de referido guardado en sesión (si hay uno) contra
    Referido y devuelve (codigo_valido_o_vacio, total_con_descuento). Nunca
    permite que alguien use su propio código."""
    code = (request.session.get('referral_code') or '').strip()
    if not code:
        return '', total_cop
    settings_row = SiteSettings.load()
    if not settings_row.referral_enabled:
        return '', total_cop
    from apps.accounts.models import Referido
    ref = Referido.objects.filter(codigo__iexact=code).select_related('usuario').first()
    if not ref or (request.user.is_authenticated and ref.usuario_id == request.user.id):
        return '', total_cop
    # el código de referido no descuenta la compra inicial — solo deja
    # registrado quién refirió, para acreditarle crédito al dueño del
    # código cuando esta compra quede aprobada (ver reward_referral_if_needed).
    return ref.codigo, total_cop


def apply_coupon_code(request, total_cop):
    """Valida el cupón guardado en sesión (si hay uno) contra Cupon y
    devuelve (codigo_valido_o_vacio, total_con_descuento). Un cupón
    'monto_fijo' está denominado en COP (la base de precios de la tienda)."""
    code = (request.session.get('coupon_code') or '').strip()
    if not code or request.session.get('referral_code'):  # solo un código por compra
        return '', total_cop
    from apps.catalog.models import Cupon
    cupon = Cupon.objects.filter(code__iexact=code).first()
    if not cupon or cupon.estado != 'Activo':
        return '', total_cop
    if cupon.tipo == 'porcentaje':
        discount = round(total_cop * cupon.valor / 100)
    else:
        discount = round(cupon.valor)  # monto fijo en COP
    # los precios COP se muestran redondeados a la centena: el total que se
    # cobra se redondea igual para que lo mostrado y lo cobrado coincidan.
    return cupon.code, max(int(round((total_cop - discount) / 100.0)) * 100, 0)


def apply_account_credit(request, total_cop):
    """Si el usuario marcó usar su crédito (sesión 'use_credit') y tiene
    saldo, lo resta del total — devuelve (monto_usado, total_restante). No
    lo descuenta de la cuenta todavía (eso solo pasa si el pago se aprueba,
    ver deduct_credit_if_needed) — si no lo marca, el crédito sigue
    acumulando intacto."""
    if not request.user.is_authenticated or not request.session.get('use_credit'):
        return 0, total_cop
    credit = request.user.credit or 0
    if credit <= 0:
        return 0, total_cop
    used = min(credit, total_cop)
    remaining = total_cop - used
    remaining = -(-int(remaining) // 100) * 100  # al alza a la centena (nunca usa más saldo del disponible)
    return total_cop - remaining, remaining


def deduct_credit_if_needed(pedido):
    """Descuenta de la cuenta el crédito usado — solo cuando el pedido
    queda aprobado (nunca antes), una sola vez por pedido."""
    if pedido.credito_usado <= 0 or pedido.credito_descontado or pedido.pago_estado != 'aprobado':
        return
    pedido.credito_descontado = True
    pedido.save(update_fields=['credito_descontado'])
    usuario = pedido.usuario
    usuario.credit = max((usuario.credit or 0) - pedido.credito_usado, 0)
    usuario.save(update_fields=['credit'])
    MovimientoCredito.objects.create(
        usuario=usuario, monto=-pedido.credito_usado,
        concepto=f'Crédito usado en la compra — pedido {pedido.ref}',
    )


def redeem_coupon_if_needed(pedido):
    """Cuenta el uso del cupón cuando el pedido queda aprobado — una sola
    vez por pedido (cupon_contabilizado), para no gastar el cupo de un
    cupón por intentos de pago que nunca se completaron."""
    if not pedido.cupon_codigo or pedido.cupon_contabilizado or pedido.pago_estado != 'aprobado':
        return
    from apps.catalog.models import Cupon
    cupon = Cupon.objects.filter(code=pedido.cupon_codigo).first()
    pedido.cupon_contabilizado = True
    pedido.save(update_fields=['cupon_contabilizado'])
    if cupon:
        cupon.usos_actuales += 1
        cupon.save(update_fields=['usos_actuales'])


def delivery_whatsapp_link(pedido):
    """Arma el mensaje con el detalle del pedido pagado, dirigido al WhatsApp
    DEL NEGOCIO (no del cliente) — para que el equipo sepa qué se pagó, con
    qué pasarela y el comprobante, y pueda hacer la entrega. wa.me nunca
    envía solo — abre el chat con el texto ya escrito, falta tocar Enviar."""
    from apps.catalog.pricing import money
    from apps.store.whatsapp import wa_link

    lines = [f'- {item.titulo}{f" (cuenta {item.cuenta})" if item.cuenta else ""} x{item.cantidad}: {money(item.precio_unitario * item.cantidad, pedido.moneda)}' for item in pedido.items.all()]
    metodo = dict(Pedido.METODO_PAGO_CHOICES).get(pedido.metodo_pago, pedido.metodo_pago)
    text = (
        f'Hola, mi pago ya quedó APROBADO, aquí el comprobante para la entrega:\n'
        f'Pedido: {pedido.ref}\n'
        f'Pasarela: {metodo}\n'
        f'Referencia de pago: {pedido.pago_referencia_externa or "—"}\n'
        + '\n'.join(lines)
        + f'\nTotal pagado: {money(pedido.total, pedido.moneda)}'
    )
    return wa_link(text)


def reward_referral_if_needed(pedido):
    """Acredita al dueño del código de referido cuando el pedido referido
    queda aprobado — una sola vez por pedido (referido_recompensado)."""
    if not pedido.referido_codigo or pedido.referido_recompensado or pedido.pago_estado != 'aprobado':
        return
    from apps.accounts.models import Referido
    ref = Referido.objects.filter(codigo=pedido.referido_codigo).select_related('usuario').first()
    if not ref:
        return
    reward = round(pedido.total * SiteSettings.load().referral_reward_pct / 100)
    pedido.referido_recompensado = True
    pedido.save(update_fields=['referido_recompensado'])
    if reward <= 0:
        return
    ref.con_compra += 1
    ref.credito_ganado += reward
    ref.save(update_fields=['con_compra', 'credito_ganado'])
    usuario = ref.usuario
    usuario.credit += reward
    usuario.save(update_fields=['credit'])
    MovimientoCredito.objects.create(
        usuario=usuario, monto=reward,
        concepto=f'Recompensa por referido — pedido {pedido.ref}',
    )
    # el comprador que usó el código (siempre tiene cuenta, la necesita para
    # pagar en línea) también recibe el mismo % en crédito, para su próxima
    # compra — apply_referral_code ya bloqueó que sea el mismo dueño del código.
    comprador = pedido.usuario
    comprador.credit += reward
    comprador.save(update_fields=['credit'])
    MovimientoCredito.objects.create(
        usuario=comprador, monto=reward,
        concepto=f'Crédito por usar código de referido — pedido {pedido.ref}',
    )


def create_pedido_from_cart(request, mode, metodo_pago):
    """Crea el Pedido + ItemPedido a partir del carrito de sesión actual.
    Devuelve None si el carrito está vacío (nada que cobrar)."""
    session_cart = Cart(request)
    lines = cart_lines(list(session_cart))
    if not lines:
        return None
    original_total = sum(l['precio_cop'] * l['cantidad'] for l in lines)
    referido_codigo, total_cop = apply_referral_code(request, original_total)
    cupon_codigo, total_cop = apply_coupon_code(request, total_cop)
    credito_usado, total_cop = apply_account_credit(request, total_cop)
    pedido = Pedido.objects.create(
        usuario=request.user, total=total_cop, moneda='COP',
        metodo_pago=metodo_pago, pago_estado='pendiente',
        referido_codigo=referido_codigo, cupon_codigo=cupon_codigo,
        credito_usado=credito_usado,
    )
    # los ítems deben sumar EXACTO lo mismo que pedido.total, porque Mercado
    # Pago cobra según la suma de `items`, no según `pedido.total` — si hay
    # descuento se reparte proporcionalmente entre las líneas (por subtotal,
    # no por unidad) y se vuelve a dividir entre `cantidad` al guardar.
    if total_cop != original_total and original_total > 0:
        factor = total_cop / original_total
        running = 0
        for i, l in enumerate(lines):
            subtotal_orig = l['precio_cop'] * l['cantidad']
            if i == len(lines) - 1:
                subtotal = total_cop - running
            else:
                subtotal = round(subtotal_orig * factor)
                running += subtotal
            precio_unitario = round(subtotal / l['cantidad'])
            ItemPedido.objects.create(
                pedido=pedido, juego=l['juego'], titulo=l.get('order_title', l['titulo']),
                precio_unitario=precio_unitario, cantidad=l['cantidad'], cuenta=l['cuenta'],
            )
    else:
        for l in lines:
            ItemPedido.objects.create(
                pedido=pedido, juego=l['juego'], titulo=l.get('order_title', l['titulo']),
                precio_unitario=l['precio_cop'], cantidad=l['cantidad'], cuenta=l['cuenta'],
            )
    return pedido


def _abs_url(name, **kwargs):
    return f'{settings.SITE_BASE_URL}{reverse(name, kwargs=kwargs)}'


# ---- Mercado Pago -----------------------------------------------------

def create_mercadopago_preference(pedido):
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return None, 'Mercado Pago no está configurado todavía (falta el access token).'
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    items = [{
        'title': item.titulo[:250],
        'quantity': item.cantidad,
        'unit_price': float(item.precio_unitario),
        'currency_id': 'COP',
    } for item in pedido.items.all()]
    preference_data = {
        'items': items,
        'external_reference': pedido.ref,
        'back_urls': {
            'success': _abs_url('orders:mercadopago_return'),
            'failure': _abs_url('orders:mercadopago_return'),
            'pending': _abs_url('orders:mercadopago_return'),
        },
        'notification_url': _abs_url('orders:mercadopago_webhook'),
        'statement_descriptor': 'GANGAJUEGOS',
    }
    try:
        result = sdk.preference().create(preference_data)
    except Exception as e:  # noqa: BLE001 — cualquier fallo de red/SDK se reporta igual
        return None, f'No se pudo conectar con Mercado Pago: {e}'
    if result.get('status') not in (200, 201):
        return None, f"Mercado Pago rechazó la preferencia: {result.get('response')}"
    pref = result['response']
    pedido.pago_referencia_externa = pref['id']
    pedido.save(update_fields=['pago_referencia_externa'])
    init_point = pref.get('init_point') or pref.get('sandbox_init_point')
    return init_point, None


def verify_mercadopago_payment(payment_id):
    """Consulta el estado REAL de un pago en la API de Mercado Pago (nunca
    se confía en el `status` que venga como parámetro en la URL de retorno,
    ya que el cliente podría manipularlo)."""
    if not settings.MERCADOPAGO_ACCESS_TOKEN or not payment_id:
        return None
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    try:
        result = sdk.payment().get(payment_id)
    except Exception:  # noqa: BLE001
        return None
    if result.get('status') != 200:
        return None
    return result['response']


MERCADOPAGO_STATUS_MAP = {
    'approved': 'aprobado',
    'rejected': 'rechazado',
    'cancelled': 'cancelado',
    'refunded': 'cancelado',
    'charged_back': 'cancelado',
}


# ---- PayPal -------------------------------------------------------------

def _paypal_token():
    resp = requests.post(
        f'{settings.PAYPAL_API_BASE}/v1/oauth2/token',
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={'grant_type': 'client_credentials'},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()['access_token']


def create_paypal_order(pedido):
    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        return None, 'PayPal no está configurado todavía (falta el client id/secret).'
    try:
        token = _paypal_token()
    except requests.RequestException as e:
        return None, f'No se pudo autenticar con PayPal: {e}'

    rate = get_rate('USD')
    usd_total = (Decimal(pedido.total) / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    body = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': pedido.ref,
            'amount': {'currency_code': 'USD', 'value': str(usd_total)},
        }],
        'application_context': {
            # `pedido.ref` es del formato "#GS-1234" — el "#" sin codificar
            # se interpreta como fragmento de URL y NUNCA llega al servidor
            # (el navegador lo corta antes de mandar la petición), dejando
            # `?pedido=` vacío y el pedido "no encontrado" al volver.
            'return_url': _abs_url('orders:paypal_return') + f'?pedido={quote(pedido.ref)}',
            'cancel_url': _abs_url('orders:paypal_cancel') + f'?pedido={quote(pedido.ref)}',
            'brand_name': 'Ganga Juegos',
            'user_action': 'PAY_NOW',
        },
    }
    try:
        resp = requests.post(
            f'{settings.PAYPAL_API_BASE}/v2/checkout/orders',
            json=body,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=15,
        )
    except requests.RequestException as e:
        return None, f'No se pudo conectar con PayPal: {e}'
    if resp.status_code not in (200, 201):
        return None, f'PayPal rechazó la orden: {resp.text}'
    data = resp.json()
    pedido.pago_referencia_externa = data['id']
    pedido.save(update_fields=['pago_referencia_externa'])
    approve_link = next((l['href'] for l in data['links'] if l['rel'] == 'approve'), None)
    return approve_link, None


def capture_paypal_order(order_id):
    """Confirma (captura) el cobro en PayPal. Se llama server-to-server con
    nuestras propias credenciales al volver del approve — nunca se confía en
    que el simple hecho de volver a esta URL signifique que se pagó."""
    token = _paypal_token()
    resp = requests.post(
        f'{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        timeout=15,
    )
    return resp
