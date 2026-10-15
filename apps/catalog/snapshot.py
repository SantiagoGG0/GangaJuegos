"""Caché en memoria del catálogo activo.

Con miles de juegos, consultar y "dar forma" a todo el catálogo en cada
página (menú, conteos por género, rieles del home, catálogo…) era lo que más
tiempo de servidor costaba. Aquí se calcula una sola vez por proceso y se
reutiliza hasta que el catálogo cambia.

Cómo se invalida entre los workers de gunicorn: cualquier cambio en juegos,
carátulas, videos del hero o tasas de cambio llama a `bump()` (vía señales,
ver apps.py), que reescribe un archivo testigo. Cada request compara la fecha
de modificación de ese archivo (un `stat`, microsegundos) y, si cambió, ese
proceso descarta su caché. Además, por seguridad, la caché vence sola a los
`TTL` segundos."""
import os
import time

from django.conf import settings

TTL = 300
_state = {'stamp': None, 'at': 0.0, 'data': {}}


def _stamp_path():
    return getattr(settings, 'CATALOG_STAMP_FILE', settings.BASE_DIR / '.catalog_version')


def _current_stamp():
    try:
        return os.stat(_stamp_path()).st_mtime_ns
    except OSError:
        return 0


def bump(**kwargs):
    """Marca el catálogo como cambiado para todos los procesos."""
    _state['stamp'] = None
    try:
        with open(_stamp_path(), 'w', encoding='ascii') as fh:
            fh.write(str(time.time_ns()))
    except OSError:
        pass


def version():
    """Versión actual del catálogo (sirve para URLs cacheables)."""
    cached('__version__', lambda: None)
    return _state['stamp'] or 0


def cached(key, builder):
    now = time.monotonic()
    stamp = _current_stamp()
    if stamp != _state['stamp'] or now - _state['at'] > TTL:
        _state.update(stamp=stamp, at=now, data={})
    data = _state['data']
    if key not in data:
        data[key] = builder()
    return data[key]


def active_games():
    """Juegos activos con su carátula, ordenados por título. No mutar."""
    from .models import Juego
    return cached('games', lambda: list(Juego.objects.filter(active=True).select_related('cover').order_by('title')))


def shaped_games(currency):
    """{pk: shape_game(...)} de todos los juegos activos en la divisa dada. No mutar."""
    from .presentation import shape_game
    from .pricing import clear_rates_cache

    def build():
        clear_rates_cache()  # que los precios usen las tasas recién guardadas
        return {g.pk: shape_game(g, currency=currency) for g in active_games()}
    return cached(('shaped', currency), build)
