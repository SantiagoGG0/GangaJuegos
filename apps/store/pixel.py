"""Cola de eventos del píxel de Meta para acciones que terminan en un
redirect (agregar a deseos, registro, etc.) — no hay HTML propio donde
meter el `fbq('track', ...)` en esa misma respuesta, así que se guarda en
sesión y `base.html` lo dispara (y lo descarta) en el siguiente render."""


def queue_pixel_event(request, name, params=None):
    request.session['pixel_event'] = {'name': name, 'params': params or {}}
