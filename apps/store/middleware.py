TRACK_PREFIXES = ('/admin', '/static/', '/media/', '/carrito/agregar', '/carrito/quitar', '/carrito/vaciar', '/buscar/')


class VisitTrackingMiddleware:
    """Registra una `SiteEvent(kind='visita')` real por cada página vista por
    un visitante, para que el panel de administración muestre tráfico real
    en vez de las cifras fijas del prototipo. Deliberadamente mínimo: sin
    IP, sin cookies propias, sin fingerprinting — solo un conteo agregado.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == 'GET'
            and response.status_code == 200
            and not request.headers.get('x-requested-with') == 'XMLHttpRequest'
            and not any(request.path.startswith(p) for p in TRACK_PREFIXES)
        ):
            content_type = response.get('Content-Type', '')
            if content_type.startswith('text/html'):
                try:
                    from apps.catalog.models import SiteEvent
                    SiteEvent.objects.create(kind='visita')
                except Exception:  # noqa: BLE001 — nunca debe romper la respuesta real
                    pass
        return response


COUNTRY_COOKIE = 'gj_pais'
COUNTRY_COOKIE_AGE = 365 * 24 * 3600


class CountryCookieMiddleware:
    """El país/moneda elegido se guarda en la sesión y, además, en una cookie
    de un año: si la sesión vence, el visitante no tiene que volver a elegir.
    Aquí se copia de la cookie a la sesión cuando la sesión no lo tiene."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        code = request.COOKIES.get(COUNTRY_COOKIE)
        if code and 'currency' not in request.session and not request.path.startswith(('/admin', '/static/', '/media/')):
            from .context_processors import _countries
            if code in {c['code'] for c in _countries(code)}:
                request.session['currency'] = code
        return self.get_response(request)
