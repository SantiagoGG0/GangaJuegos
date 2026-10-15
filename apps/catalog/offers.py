"""Ofertas de juegos (pestaña Ofertas del panel).

Una oferta se guarda directamente en el juego: el precio actual pasa a ser
el "precio anterior" (tachado en la tienda) y el nuevo precio es el
descontado. Quitar la oferta —a mano o porque pasó su fecha de término—
restaura el precio anterior."""
import time

from django.utils import timezone

from .models import Juego


def _round100(value):
    return int(round(value / 100.0)) * 100


def apply_offer(juego, pct, ends=None):
    """Aplica un descuento de `pct`% sobre el precio base (si el juego ya
    estaba en oferta, sobre su precio anterior, no se apila)."""
    pct = max(1, min(int(pct), 95))
    base_p = juego.old_price_primary or juego.price_primary
    base_s = juego.old_price_secondary or juego.price_secondary
    juego.old_price_primary = base_p
    juego.old_price_secondary = base_s
    juego.price_primary = _round100(base_p * (1 - pct / 100))
    juego.price_secondary = _round100(base_s * (1 - pct / 100))
    juego.oferta_termina = ends
    juego.save(update_fields=['old_price_primary', 'old_price_secondary', 'price_primary', 'price_secondary', 'oferta_termina'])


def remove_offer(juego):
    if juego.old_price_primary:
        juego.price_primary = juego.old_price_primary
    if juego.old_price_secondary:
        juego.price_secondary = juego.old_price_secondary
    juego.old_price_primary = None
    juego.old_price_secondary = None
    juego.oferta_termina = None
    juego.save(update_fields=['old_price_primary', 'old_price_secondary', 'price_primary', 'price_secondary', 'oferta_termina'])


_LAST_CHECK = {'at': 0.0}


def expire_offers(force=False):
    """Retira las ofertas cuya fecha de término ya pasó. Se llama en cada
    request de la tienda pero solo consulta la base como máximo una vez por
    minuto."""
    now = time.monotonic()
    if not force and now - _LAST_CHECK['at'] < 60:
        return
    _LAST_CHECK['at'] = now
    try:
        for juego in Juego.objects.filter(oferta_termina__lt=timezone.localdate()):
            remove_offer(juego)
    except Exception:  # noqa: BLE001 — nunca debe romper una página
        pass
