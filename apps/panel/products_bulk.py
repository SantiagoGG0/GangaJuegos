"""Carga masiva de juegos (pestaña "Carga masiva" del panel).

Flujo del diseño en 3 pasos: 1) descargar la plantilla CSV, 2) subir el
archivo (CSV o Excel con las mismas columnas), 3) revisar la validación
fila por fila e importar solo las filas válidas. Si ya existe un juego con
el mismo slug (generado del título) se ACTUALIZA en vez de duplicarse."""
import csv
import io
import re

import requests
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.catalog.models import Cover, Juego, PLATFORM_CHOICES
from apps.catalog.pricing import money

COLUMNS = ['titulo', 'plataforma', 'genero', 'precio_primaria', 'precio_secundaria', 'precio_anterior', 'caratula_url']
PLATFORM_VALUES = [c[0] for c in PLATFORM_CHOICES]
SESSION_KEY = 'bulk_rows'
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def _ctx(request):
    from .dashboard_views import base_context
    return base_context(request, 'carga')


def _norm_platform(raw):
    raw = (raw or '').strip().upper().replace(' ', '').replace('-', '/').replace('Y', '/')
    for value in PLATFORM_VALUES:
        if raw == value.upper():
            return value
    return None


def _price(raw):
    raw = str(raw if raw is not None else '').strip()
    if not raw:
        return None
    cleaned = re.sub(r'[^\d,.]', '', raw)
    if re.fullmatch(r'\d{1,3}([.,]\d{3})+', cleaned):
        cleaned = re.sub(r'[.,]', '', cleaned)
    try:
        value = int(round(float(cleaned.replace(',', '.'))))
    except ValueError:
        return False
    return value if value > 0 else False


def _read_rows(f):
    """Devuelve una lista de dicts {columna: valor} leyendo CSV (coma o
    punto y coma) o XLSX con encabezados en la primera fila."""
    name = f.name.lower()
    if name.endswith('.xlsx'):
        import openpyxl
        wb = openpyxl.load_workbook(f, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        header = [str(h or '').strip().lower() for h in rows[0]]
        return [{header[i]: (r[i] if i < len(r) else None) for i in range(len(header))} for r in rows[1:]]
    data = f.read()
    for enc in ('utf-8-sig', 'latin-1'):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:2048]
    delim = ';' if sample.count(';') > sample.count(',') else ','
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    reader.fieldnames = [(h or '').strip().lower() for h in (reader.fieldnames or [])]
    return list(reader)


def _validate(raw):
    def val(k):
        v = raw.get(k)
        return str(v).strip() if v is not None else ''
    title, genre = val('titulo'), val('genero')
    plat_raw = val('plataforma')
    plat = _norm_platform(plat_raw)
    prim, sec, old = _price(raw.get('precio_primaria')), _price(raw.get('precio_secundaria')), _price(raw.get('precio_anterior'))
    if not title:
        err = 'Falta título'
    elif not plat:
        err = 'Plataforma no válida'
    elif not genre:
        err = 'Falta género'
    elif not prim:
        err = 'Falta precio primaria' if prim is None else 'Precio primaria no válido'
    elif not sec:
        err = 'Falta precio secundaria' if sec is None else 'Precio secundaria no válido'
    elif old is False:
        err = 'Precio anterior no válido'
    else:
        err = ''
    return {
        'title': title, 'plat': plat or plat_raw, 'genre': genre, 'prim': prim or None, 'sec': sec or None,
        'old': old or None, 'cover_url': val('caratula_url'), 'err': err,
    }


def products_bulk_view(request):
    ctx = _ctx(request)
    data = request.session.get(SESSION_KEY)
    if data:
        rows = data['rows']
        ok = sum(1 for r in rows if not r['err'])
        ctx.update({
            'loaded': True, 'file_name': data['name'], 'n_rows': len(rows), 'ok_count': ok, 'err_count': len(rows) - ok,
            'imported': data.get('imported'), 'import_errors': data.get('import_errors', []),
            'rows': [{**r, 'prim_f': money(r['prim'], allow_free=False) if r['prim'] else '—',
                      'sec_f': money(r['sec'], allow_free=False) if r['sec'] else '—',
                      'genre': r['genre'] or '—'} for r in rows],
        })
    ctx['columns'] = COLUMNS
    ctx['upload_error'] = request.session.pop('bulk_error', None)
    return render(request, 'panel/carga.html', ctx)


def products_bulk_template(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="plantilla-juegos-gangajuegos.csv"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(COLUMNS)
    writer.writerow(['Hogwarts Legacy', 'PS5', 'Aventura', '149900', '94900', '', ''])
    writer.writerow(['Ghost of Tsushima', 'PS4', 'Acción', '99900', '64900', '139900', 'https://ejemplo.com/caratula.jpg'])
    return response


@require_POST
def products_bulk_upload(request):
    f = request.FILES.get('file')
    if not f or not f.name.lower().endswith(('.csv', '.xlsx')):
        request.session['bulk_error'] = 'Sube un archivo .csv (o .xlsx) con las columnas de la plantilla.'
        return redirect('gsadmin:products_bulk')
    try:
        raw_rows = _read_rows(f)
    except Exception as e:  # noqa: BLE001
        request.session['bulk_error'] = f'No se pudo leer el archivo: {e}'
        return redirect('gsadmin:products_bulk')
    rows = [_validate(r) for r in raw_rows if any(str(v or '').strip() for v in r.values())]
    if not rows:
        request.session['bulk_error'] = 'El archivo no tiene filas con datos.'
        return redirect('gsadmin:products_bulk')
    request.session[SESSION_KEY] = {'name': f.name, 'rows': rows[:2000]}
    return redirect('gsadmin:products_bulk')


def _fetch_image(url):
    url = url.strip()
    starts = [m.start() for m in re.finditer(r'https?://', url)]
    if len(starts) > 1:
        url = url[starts[-1]:]
    if not url.lower().startswith(('http://', 'https://')):
        return None, 'la URL de la carátula debe empezar con http:// o https://'
    try:
        resp = requests.get(url, timeout=(5, 8), stream=True)
        resp.raise_for_status()
        ctype = resp.headers.get('Content-Type', '')
        if not ctype.startswith('image/'):
            return None, 'la URL de la carátula no apunta a una imagen'
        chunks, total = [], 0
        for chunk in resp.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                return None, 'la carátula pesa más de 8 MB'
            chunks.append(chunk)
    except requests.RequestException as e:
        return None, f'no se pudo descargar la carátula ({e})'
    ext = ctype.split('/')[-1].split(';')[0].strip() or 'jpg'
    return ContentFile(b''.join(chunks), name=f'import.{"jpg" if ext == "jpeg" else ext}'), None


@require_POST
def products_bulk_import(request):
    data = request.session.get(SESSION_KEY)
    if not data or data.get('imported'):
        return redirect('gsadmin:products_bulk')
    n, errors = 0, []
    for r in data['rows']:
        if r['err']:
            continue
        old_p = r['old'] if r['old'] and r['old'] > r['prim'] else None
        old_s = round(old_p * r['sec'] / r['prim'] / 100) * 100 if old_p else None
        slug = slugify(r['title'])[:180] or 'juego'
        juego, created = Juego.objects.get_or_create(slug=slug, defaults={
            'title': r['title'], 'platform': r['plat'], 'genre': r['genre'],
            'price_primary': r['prim'], 'price_secondary': r['sec'],
            'old_price_primary': old_p, 'old_price_secondary': old_s, 'active': True,
        })
        if not created:
            juego.title, juego.platform, juego.genre = r['title'], r['plat'], r['genre']
            juego.price_primary, juego.price_secondary = r['prim'], r['sec']
            juego.old_price_primary, juego.old_price_secondary = old_p, old_s
            juego.save()
        n += 1
        if r['cover_url']:
            content, err = _fetch_image(r['cover_url'])
            if err:
                errors.append(f'{r["title"]}: {err}')
            else:
                existing = Cover.objects.filter(juego=juego).first()
                if existing:
                    existing.image.delete(save=False)
                Cover.objects.update_or_create(juego=juego, defaults={'image': content})
    data['imported'] = n
    data['import_errors'] = errors[:30]
    request.session[SESSION_KEY] = data
    return redirect('gsadmin:products_bulk')


@require_POST
def products_bulk_reset(request):
    request.session.pop(SESSION_KEY, None)
    return redirect('gsadmin:products_bulk')
