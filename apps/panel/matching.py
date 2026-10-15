"""Puerto literal del algoritmo matchSlug() de "Gestor de carátulas.dc.html":
normaliza el nombre de archivo (sin tildes, minúsculas, alfanumérico) y lo
compara contra título/slug de cada juego en 3 niveles: exacto, prefijo, o
substring (si el nombre normalizado mide 6+ caracteres)."""
import re
import unicodedata


def slugify_js(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9]+', '-', text.lower())
    return text.strip('-')


def norm(text):
    return slugify_js(text).replace('-', '')


def match_slug(filename, games):
    """games: iterable de (slug, title)."""
    base = re.sub(r'\.[a-zA-Z0-9]+$', '', filename)
    n = norm(base)
    if not n:
        return None

    for slug, title in games:
        if norm(title) == n or slug == slugify_js(base):
            return slug

    for slug, title in games:
        tn = norm(title)
        if tn.startswith(n) or n.startswith(tn):
            return slug

    if len(n) >= 6:
        for slug, title in games:
            if n in norm(title):
                return slug

    return None
