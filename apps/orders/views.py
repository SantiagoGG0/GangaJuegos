from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.catalog.models import Combo, Juego
from apps.catalog.models import PlusPlan

from . import payments
from .cart import Cart
from .models import Pedido


@require_POST
def cart_add(request):
    from apps.catalog.models import GiftCard
    from apps.store.pixel import queue_pixel_event

    cart = Cart(request)
    item_type = request.POST.get('type')
    item_id = request.POST.get('id')
    acc = request.POST.get('acc', 'primaria')
    if acc not in ('primaria', 'secundaria'):
        acc = 'primaria'
    prim = acc == 'primaria'

    if item_type == 'juego':
        juego = get_object_or_404(Juego, pk=item_id, active=True)
        title = juego.title
        price_cop = juego.price_primary if prim else juego.price_secondary
    elif item_type == 'combo':
        combo = get_object_or_404(Combo, pk=item_id)
        title = combo.title
        price_cop = combo.price_primary if prim else combo.price_secondary
    elif item_type == 'plan':
        plan = get_object_or_404(PlusPlan, pk=item_id)
        title = f'PS Plus {plan.tier}'
        price_cop = plan.price
    elif item_type == 'gift':
        gift = get_object_or_404(GiftCard, pk=item_id)
        title = f'Gift card PSN USD {gift.denomination}'
        price_cop = gift.price
    else:
        return redirect(request.META.get('HTTP_REFERER', '/'))

    cart.add(item_type, item_id, acc=acc)
    from apps.catalog.models import SiteEvent
    SiteEvent.objects.create(kind='carrito')

    pixel_params = {
        'content_ids': [str(item_id)], 'content_type': 'product',
        'content_name': title, 'value': price_cop, 'currency': 'COP',
    }
    if request.headers.get('X-Requested-With') == 'fetch':
        return JsonResponse({
            'title': title, 'cart_count': len(cart),
            'pixel_event': {'name': 'AddToCart', 'params': pixel_params},
        })
    queue_pixel_event(request, 'AddToCart', pixel_params)
    if request.POST.get('next') == 'cart':
        return redirect('store:cart')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@require_POST
def cart_remove(request, index):
    cart = Cart(request)
    cart.remove(int(index))
    return redirect(request.META.get('HTTP_REFERER', 'store:cart'))


@require_POST
def cart_clear(request):
    Cart(request).clear()
    return redirect(request.META.get('HTTP_REFERER', 'store:cart'))


@require_POST
def cart_set_qty(request, index):
    try:
        qty = int(request.POST.get('qty', 1))
    except ValueError:
        qty = 1
    Cart(request).set_qty(int(index), qty)
    return redirect(request.META.get('HTTP_REFERER', 'store:cart'))


def _price_mode(request):
    return request.session.get('price_mode', 'Primaria')


@require_POST
def apply_referral(request):
    from apps.accounts.models import Referido
    from apps.catalog.models import SiteSettings

    code = request.POST.get('code', '').strip()
    if not code:
        return redirect('store:cart')
    if not SiteSettings.load().referral_enabled:
        messages.error(request, 'Los códigos de referido no están habilitados ahora mismo.', extra_tags='cart ref')
        return redirect('store:cart')
    ref = Referido.objects.filter(codigo__iexact=code).select_related('usuario').first()
    if not ref or (request.user.is_authenticated and ref.usuario_id == request.user.id):
        messages.error(request, 'Ese código de referido no es válido.', extra_tags='cart ref')
        return redirect('store:cart')
    request.session.pop('coupon_code', None)  # solo un código por compra
    request.session['referral_code'] = ref.codigo
    messages.success(request, f'Código de referido "{ref.codigo}" aplicado.', extra_tags='cart ref')
    return redirect('store:cart')


@require_POST
def remove_referral(request):
    request.session.pop('referral_code', None)
    return redirect('store:cart')


@require_POST
def apply_coupon(request):
    from apps.catalog.models import Cupon

    code = request.POST.get('code', '').strip()
    if not code:
        return redirect('store:cart')
    cupon = Cupon.objects.filter(code__iexact=code).first()
    if not cupon:
        messages.error(request, 'Ese cupón no existe.', extra_tags='cart')
        return redirect('store:cart')
    if cupon.estado != 'Activo':
        messages.error(request, 'Ese cupón ya venció o se agotó.', extra_tags='cart')
        return redirect('store:cart')
    request.session.pop('referral_code', None)  # solo un código por compra
    request.session['coupon_code'] = cupon.code
    messages.success(request, f'Cupón aplicado: {cupon.valor_display} de descuento', extra_tags='cart')
    return redirect('store:cart')


@require_POST
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    return redirect('store:cart')


@login_required
@require_POST
def toggle_credit(request):
    if request.POST.get('use_credit') == 'on':
        request.session['use_credit'] = True
    else:
        request.session.pop('use_credit', None)
    return redirect('store:cart')


@login_required
@require_POST
def checkout_mercadopago(request):
    from apps.catalog.models import SiteSettings
    if not SiteSettings.load().mercadopago_enabled:
        messages.error(request, 'Mercado Pago no está disponible en este momento.', extra_tags='cart')
        return redirect('store:cart')
    pedido = payments.create_pedido_from_cart(request, _price_mode(request), 'mercadopago')
    if not pedido:
        messages.error(request, 'Tu carrito está vacío.', extra_tags='cart')
        return redirect('store:cart')
    init_point, error = payments.create_mercadopago_preference(pedido)
    if error:
        pedido.delete()
        messages.error(request, error, extra_tags='cart')
        return redirect('store:cart')
    return redirect(init_point)


@login_required
@require_POST
def checkout_paypal(request):
    from apps.catalog.models import SiteSettings
    if not SiteSettings.load().paypal_enabled:
        messages.error(request, 'PayPal no está disponible en este momento.', extra_tags='cart')
        return redirect('store:cart')
    pedido = payments.create_pedido_from_cart(request, _price_mode(request), 'paypal')
    if not pedido:
        messages.error(request, 'Tu carrito está vacío.', extra_tags='cart')
        return redirect('store:cart')
    approve_link, error = payments.create_paypal_order(pedido)
    if error:
        pedido.delete()
        messages.error(request, error, extra_tags='cart')
        return redirect('store:cart')
    return redirect(approve_link)


def _payment_result_context(request, pedido):
    import json

    from apps.catalog.pricing import money
    if not pedido:
        return {'pedido': None}
    items = list(pedido.items.all())
    ctx = {
        'pedido': pedido,
        'total_display': money(pedido.total, pedido.moneda),
        'items': items,
    }
    if pedido.pago_estado == 'aprobado':
        ctx['whatsapp_delivery_link'] = payments.delivery_whatsapp_link(pedido)
        # el Purchase del píxel solo se dispara la primera vez que se ve esta
        # confirmación — si no, cada refresh/vuelta a la página contaría la
        # misma venta otra vez y desinflaría las métricas de conversión.
        already_sent = request.session.setdefault('pixel_purchases_sent', [])
        if pedido.ref not in already_sent:
            already_sent.append(pedido.ref)
            request.session.modified = True
            purchase_pixel = {
                'content_ids': [str(i.juego_id) if i.juego_id else i.titulo for i in items],
                'value': float(pedido.total), 'currency': pedido.moneda,
                'num_items': sum(i.cantidad for i in items),
            }
            ctx['purchase_pixel_json'] = json.dumps(purchase_pixel).replace('<', '\\u003c')
    return ctx


def _on_approved(pedido, prev_estado):
    """Efectos de que un pedido quede aprobado (recompensa de referido +
    evento para el panel), sin depender de la sesión — así sirve tanto para
    la vista de retorno (con sesión del comprador) como para el webhook
    (llamada servidor-a-servidor de Mercado Pago, sin sesión real)."""
    payments.reward_referral_if_needed(pedido)
    payments.redeem_coupon_if_needed(pedido)
    payments.deduct_credit_if_needed(pedido)
    if prev_estado != 'aprobado':
        from apps.catalog.models import SiteEvent
        SiteEvent.objects.create(kind='compra')


def mercadopago_return(request):
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    payment = payments.verify_mercadopago_payment(payment_id) if payment_id else None
    # el external_reference verificado con la API de Mercado Pago manda
    # sobre el que venga en la URL de retorno — a veces MP no lo agrega al
    # link (o llega vacío) y el pedido no aparecía ("No encontramos ese
    # pedido") aunque el pago sí se hubiera aprobado.
    ref = (payment.get('external_reference') if payment else None) or request.GET.get('external_reference')
    pedido = Pedido.objects.filter(ref=ref).first() if ref else None
    if pedido and payment:
        prev_estado = pedido.pago_estado
        estado = payments.MERCADOPAGO_STATUS_MAP.get(payment.get('status'), 'pendiente')
        pedido.pago_estado = estado
        pedido.save(update_fields=['pago_estado'])
        if estado == 'aprobado':
            _on_approved(pedido, prev_estado)
            Cart(request).clear()
            request.session.pop('referral_code', None)
            request.session.pop('coupon_code', None)
            request.session.pop('use_credit', None)
    return render(request, 'store/payment_result.html', _payment_result_context(request, pedido))


@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """Notificación asíncrona de Mercado Pago. Nunca confía en el cuerpo del
    POST directamente — vuelve a consultar el pago con nuestro access token
    para saber su estado real, igual que en la vista de retorno."""
    payment_id = request.GET.get('data.id') or request.POST.get('data.id')
    if payment_id:
        payment = payments.verify_mercadopago_payment(payment_id)
        if payment:
            ref = payment.get('external_reference')
            pedido = Pedido.objects.filter(ref=ref).first()
            if pedido:
                prev_estado = pedido.pago_estado
                nuevo_estado = payments.MERCADOPAGO_STATUS_MAP.get(payment.get('status'), pedido.pago_estado)
                pedido.pago_estado = nuevo_estado
                pedido.save(update_fields=['pago_estado'])
                if nuevo_estado == 'aprobado':
                    _on_approved(pedido, prev_estado)
    return HttpResponse(status=200)


def paypal_return(request):
    order_id = request.GET.get('token')  # PayPal manda el order id como "token"
    ref = request.GET.get('pedido')
    pedido = Pedido.objects.filter(ref=ref).first() if ref else None
    if pedido and order_id:
        try:
            resp = payments.capture_paypal_order(order_id)
        except Exception:  # noqa: BLE001
            resp = None
        if resp is not None and resp.status_code in (200, 201):
            data = resp.json()
            if data.get('status') == 'COMPLETED':
                prev_estado = pedido.pago_estado
                pedido.pago_estado = 'aprobado'
                pedido.save(update_fields=['pago_estado'])
                _on_approved(pedido, prev_estado)
                Cart(request).clear()
                request.session.pop('referral_code', None)
                request.session.pop('coupon_code', None)
                request.session.pop('use_credit', None)
            else:
                pedido.pago_estado = 'rechazado'
                pedido.save(update_fields=['pago_estado'])
        else:
            pedido.pago_estado = 'rechazado'
            pedido.save(update_fields=['pago_estado'])
    return render(request, 'store/payment_result.html', _payment_result_context(request, pedido))


def paypal_cancel(request):
    ref = request.GET.get('pedido')
    pedido = Pedido.objects.filter(ref=ref).first() if ref else None
    if pedido:
        pedido.pago_estado = 'cancelado'
        pedido.save(update_fields=['pago_estado'])
    return render(request, 'store/payment_result.html', _payment_result_context(request, pedido))
