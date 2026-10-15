"""Carga masiva de juegos (pestaña "Carga masiva" del panel).

Flujo del diseño en 3 pasos: 1) descargar la plantilla, 2) subir el archivo
(XLSX o CSV con las columnas de la plantilla), 3) revisar la validación fila
por fila e importar solo las filas válidas. Si ya existe un juego con el mismo
slug (el de la columna Slug o, si va vacía, el generado del título) se
ACTUALIZA en vez de duplicarse.

Los encabezados se reconocen sin importar tildes, mayúsculas, asteriscos ni el
texto de ayuda entre paréntesis ("Título *", "Precio cuenta primaria (COP)"…),
así que también se aceptan los nombres cortos de la plantilla antigua
(titulo, precio_primaria, caratula_url…).

Las carátulas pueden venir como URL o como imagen pegada en la fila (imagen
flotante anclada a la celda o imagen "dentro de la celda" de Excel 365). Las
imágenes pegadas se guardan en `bulk_tmp/` hasta que se confirma la importación.
Toda carátula importada se reduce a 600 px de ancho y se guarda en WebP.

La importación se hace por tandas de pocos segundos (la página encadena las
tandas sola) para que un archivo de miles de filas con carátulas por URL no
supere el tiempo máximo de una petición."""
import csv
import hashlib
import io
import posixpath
import re
import time
import unicodedata
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as ET

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.catalog.models import Cover, Juego, PLATFORM_CHOICES
from apps.catalog.pricing import money

# (clave interna, encabezado de la plantilla, ¿obligatoria?)
TEMPLATE_COLUMNS = [
    ('titulo', 'Título *'),
    ('slug', 'Slug (déjalo vacío para generarlo del título)'),
    ('plataforma', 'Plataforma *'),
    ('genero', 'Género *'),
    ('precio_secundaria', 'Precio cuenta secundaria (COP) *'),
    ('precio_primaria', 'Precio cuenta primaria (COP) *'),
    ('precio_anterior_secundaria', 'Precio antes — secundaria (COP, opcional)'),
    ('precio_anterior_primaria', 'Precio antes — primaria (COP, opcional)'),
    ('activo', 'Activo (SI/NO) *'),
    ('destacado', 'Destacado (SI/NO) *'),
    ('frase', 'Frase destacada (solo si es destacado)'),
    ('notas', 'Notas internas'),
    ('caratula_url', 'URL de la carátula (opcional, alternativa a pegarla)'),
    ('caratula', 'Carátula (pega la imagen en la celda de abajo)'),
]
COLUMNS = [label for _, label in TEMPLATE_COLUMNS]

# Encabezado normalizado -> clave interna.
HEADER_ALIASES = {
    'titulo': 'titulo', 'title': 'titulo', 'nombre': 'titulo', 'juego': 'titulo',
    'slug': 'slug',
    'plataforma': 'plataforma', 'platform': 'plataforma',
    'genero': 'genero', 'genre': 'genero',
    'precio cuenta secundaria': 'precio_secundaria', 'precio secundaria': 'precio_secundaria',
    'precio cuenta primaria': 'precio_primaria', 'precio primaria': 'precio_primaria',
    'precio antes secundaria': 'precio_anterior_secundaria',
    'precio anterior secundaria': 'precio_anterior_secundaria',
    'precio antes cuenta secundaria': 'precio_anterior_secundaria',
    'precio antes primaria': 'precio_anterior_primaria',
    'precio anterior primaria': 'precio_anterior_primaria',
    'precio antes cuenta primaria': 'precio_anterior_primaria',
    'precio anterior': 'precio_anterior_primaria', 'precio antes': 'precio_anterior_primaria',
    'activo': 'activo', 'active': 'activo',
    'destacado': 'destacado', 'featured': 'destacado',
    'frase destacada': 'frase', 'frase': 'frase', 'tagline': 'frase',
    'notas internas': 'notas', 'notas': 'notas',
    'url de la caratula': 'caratula_url', 'caratula url': 'caratula_url', 'url caratula': 'caratula_url',
    'url de caratula': 'caratula_url', 'url imagen': 'caratula_url', 'url de la imagen': 'caratula_url',
    'caratula': 'caratula', 'imagen': 'caratula', 'caratula imagen': 'caratula',
}

PLATFORM_VALUES = [c[0] for c in PLATFORM_CHOICES]
TRUE_VALUES = {'si', 's', 'yes', 'y', 'true', 'verdadero', '1', 'x'}
FALSE_VALUES = {'no', 'n', 'false', 'falso', '0'}
SESSION_KEY = 'bulk_rows'
TMP_DIR = 'bulk_tmp'
MAX_ROWS = 5000
MAX_IMAGE_BYTES = 8 * 1024 * 1024
COVER_MAX_WIDTH = 600  # las carátulas se guardan a este ancho máximo, en WebP
COVER_QUALITY = 82
IMPORT_TIME_BUDGET = 12  # segundos por tanda de importación
IMPORT_BATCH = 24        # filas por sub-tanda (carátulas descargadas en paralelo)
TITLE_MAX = Juego._meta.get_field('title').max_length
GENRE_MAX = Juego._meta.get_field('genre').max_length
TAGLINE_MAX = Juego._meta.get_field('tagline').max_length
SLUG_MAX = Juego._meta.get_field('slug').max_length


def _ctx(request):
    from .dashboard_views import base_context
    return base_context(request, 'carga')


def _strip_accents(s):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', s) if not unicodedata.combining(ch))


def _norm_header(raw):
    h = _strip_accents(str(raw or '')).lower()
    h = re.sub(r'\(.*?\)', ' ', h)
    h = re.sub(r'[*:]', ' ', h)
    h = re.sub(r'[\s_\-—–/.]+', ' ', h).strip()
    return HEADER_ALIASES.get(h, h)


def _text(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r'\s+', ' ', str(v).replace('\xa0', ' ')).strip()


def _norm_platform(raw):
    s = _text(raw).upper()
    found = set(re.findall(r'PS\s*([45])', s))
    if not found:
        return None
    value = '/'.join(f'PS{n}' for n in sorted(found))
    return value if value in PLATFORM_VALUES else None


def _price(raw):
    if isinstance(raw, bool):
        return False
    if isinstance(raw, (int, float)):
        value = int(round(raw))
        return value if value > 0 else False
    raw = _text(raw)
    if not raw:
        return None
    cleaned = re.sub(r'[^\d,.]', '', raw)
    if not cleaned:
        return False
    if re.fullmatch(r'\d{1,3}([.,]\d{3})+', cleaned):
        cleaned = re.sub(r'[.,]', '', cleaned)
    elif re.fullmatch(r'\d{1,3}(\.\d{3})+,\d+', cleaned):
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'\d{1,3}(,\d{3})+\.\d+', cleaned):
        cleaned = cleaned.replace(',', '')
    try:
        value = int(round(float(cleaned.replace(',', '.'))))
    except ValueError:
        return False
    return value if value > 0 else False


def _yes_no(raw, default):
    """True/False según SI/NO; `default` si está vacío; 'bad' si no se entiende."""
    if isinstance(raw, bool):
        return raw
    s = _strip_accents(_text(raw)).lower().rstrip('.')
    if not s:
        return default
    if s in TRUE_VALUES:
        return True
    if s in FALSE_VALUES:
        return False
    return 'bad'


def _make_slug(raw_slug, title):
    slug = slugify(_text(raw_slug))[:SLUG_MAX].strip('-')
    if not slug:
        slug = slugify(title)[:SLUG_MAX].strip('-')
    if not slug:
        # Títulos sin letras latinas (p. ej. solo japonés): slug estable a partir del título.
        slug = 'juego-' + hashlib.sha1(title.encode('utf-8')).hexdigest()[:10]
    return slug


# ---------------------------------------------------------------- lectura

def _sniff_image(data):
    """Extensión de la imagen (jpg/png/gif/webp) o None si no es una imagen usable."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or '').lower()
        img.verify()
    except Exception:  # noqa: BLE001
        return None
    return {'jpeg': 'jpg', 'mpo': 'jpg', 'png': 'png', 'gif': 'gif', 'webp': 'webp'}.get(fmt)


def _rich_value_images(zf, sheet_path):
    """Imágenes "dentro de la celda" de Excel 365 (Insertar → Imagen en celda).
    openpyxl no las lee, así que se resuelven a mano desde el XML:
    celda vm -> metadata.xml -> rdrichvalue.xml -> richValueRel.xml -> imagen.
    Devuelve {fila (1-based): bytes}."""
    names = set(zf.namelist())
    needed = ['xl/metadata.xml', 'xl/richData/rdrichvalue.xml', 'xl/richData/richValueRel.xml',
              'xl/richData/_rels/richValueRel.xml.rels']
    if not all(n in names for n in needed):
        return {}
    ns_main = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

    def local(tag):
        return tag.rsplit('}', 1)[-1]

    # vm (1-based) -> índice de rich value
    meta = ET.fromstring(zf.read('xl/metadata.xml'))
    rich_idx_by_bk = []
    for fm in meta.iter():
        if local(fm.tag) == 'futureMetadata' and fm.get('name') == 'XLRICHVALUE':
            for bk in fm:
                if local(bk.tag) != 'bk':
                    continue
                rvb = next((e for e in bk.iter() if local(e.tag) == 'rvb'), None)
                rich_idx_by_bk.append(int(rvb.get('i')) if rvb is not None else None)
    value_meta = []
    for vm in meta.iter():
        if local(vm.tag) == 'valueMetadata':
            for bk in vm:
                rc = next((e for e in bk if local(e.tag) == 'rc'), None)
                value_meta.append(int(rc.get('v')) if rc is not None else None)

    # índice de rich value -> índice de relación (posición de _rvRel:LocalImageIdentifier)
    key_pos = {}
    if 'xl/richData/rdrichvaluestructure.xml' in names:
        st = ET.fromstring(zf.read('xl/richData/rdrichvaluestructure.xml'))
        for i, s in enumerate(e for e in st if local(e.tag) == 's'):
            keys = [k.get('n') for k in s if local(k.tag) == 'k']
            if '_rvRel:LocalImageIdentifier' in keys:
                key_pos[i] = keys.index('_rvRel:LocalImageIdentifier')
    rv_rel = []
    for rv in ET.fromstring(zf.read('xl/richData/rdrichvalue.xml')):
        if local(rv.tag) != 'rv':
            continue
        vals = [v.text for v in rv if local(v.tag) == 'v']
        pos = key_pos.get(int(rv.get('s', 0)), 0)
        try:
            rv_rel.append(int(vals[pos]))
        except (IndexError, TypeError, ValueError):
            rv_rel.append(None)

    rel_ids = [e.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
               for e in ET.fromstring(zf.read('xl/richData/richValueRel.xml')) if local(e.tag) == 'rel']
    targets = {e.get('Id'): e.get('Target')
               for e in ET.fromstring(zf.read('xl/richData/_rels/richValueRel.xml.rels'))}

    def image_for_vm(vm):
        try:
            rc = value_meta[vm - 1]
            rich = rich_idx_by_bk[rc - 1] if rc is not None else None
            rel_idx = rv_rel[rich]
            target = targets[rel_ids[rel_idx]]
        except (IndexError, KeyError, TypeError):
            return None
        path = posixpath.normpath(posixpath.join('xl/richData', target)) if not target.startswith('/') else target[1:]
        return zf.read(path) if path in names else None

    out = {}
    for _, el in ET.iterparse(io.BytesIO(zf.read(sheet_path))):
        if el.tag == f'{ns_main}c' and el.get('vm'):
            m = re.match(r'[A-Z]+(\d+)', el.get('r', ''))
            if m:
                data = image_for_vm(int(el.get('vm')))
                if data:
                    out.setdefault(int(m.group(1)), data)
        if el.tag == f'{ns_main}row':
            el.clear()
    return out


def _sheet_path(zf, sheet_title):
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    wb = ET.fromstring(zf.read('xl/workbook.xml'))
    rels = {e.get('Id'): e.get('Target') for e in ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))}
    for s in wb.iterfind('m:sheets/m:sheet', ns):
        if s.get('name') == sheet_title:
            target = rels.get(s.get(f'{{{ns["r"]}}}id'), '')
            return target[1:] if target.startswith('/') else posixpath.normpath(posixpath.join('xl', target))
    return None


def _pick_sheet(wb):
    """La hoja "Productos" o, si no existe, la primera cuyo encabezado tenga Título."""
    for ws in wb.worksheets:
        if _strip_accents(ws.title).strip().lower() == 'productos':
            return ws
    for ws in wb.worksheets:
        first = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        if 'titulo' in {_norm_header(h) for h in first}:
            return ws
    return wb.worksheets[0]


def _read_xlsx(f):
    import openpyxl
    data = f.read()
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = _pick_sheet(wb)
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], set()
    header = [_norm_header(h) for h in rows[0]]
    images = {}
    for img in getattr(ws, '_images', []):  # imágenes flotantes ancladas a una celda
        try:
            row = img.anchor._from.row + 1
            images.setdefault(row, img._data())
        except Exception:  # noqa: BLE001
            continue
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            path = _sheet_path(zf, ws.title)
            if path:
                for row, blob in _rich_value_images(zf, path).items():
                    images.setdefault(row, blob)
    except Exception:  # noqa: BLE001
        pass
    out = []
    for n, r in enumerate(rows[1:], start=2):
        d = {header[i]: r[i] for i in range(min(len(header), len(r))) if header[i]}
        if n in images:
            d['_image'] = images[n]
        out.append(d)
    return out, set(header)


def _read_csv(f):
    data = f.read()
    text = None
    for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = text[:4096]
    delim = ';' if sample.count(';') > sample.count(',') else ','
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = list(reader)
    if not rows:
        return [], set()
    header = [_norm_header(h) for h in rows[0]]
    return [{header[i]: r[i] for i in range(min(len(header), len(r))) if header[i]} for r in rows[1:]], set(header)


def _read_rows(f):
    """Lista de dicts {clave interna: valor} y el conjunto de columnas presentes."""
    if f.name.lower().endswith('.xlsx'):
        return _read_xlsx(f)
    return _read_csv(f)


# ------------------------------------------------------------- validación

def _validate(raw, present):
    title = _text(raw.get('titulo'))
    genre = _text(raw.get('genero'))
    plat_raw = _text(raw.get('plataforma'))
    plat = _norm_platform(plat_raw)
    prim, sec = _price(raw.get('precio_primaria')), _price(raw.get('precio_secundaria'))
    old_p, old_s = _price(raw.get('precio_anterior_primaria')), _price(raw.get('precio_anterior_secundaria'))
    active = _yes_no(raw.get('activo'), True)
    featured = _yes_no(raw.get('destacado'), False)
    if not title:
        err = 'Falta título'
    elif not plat:
        err = 'Falta plataforma' if not plat_raw else f'Plataforma no válida ({plat_raw})'
    elif not genre:
        err = 'Falta género'
    elif not prim:
        err = 'Falta precio primaria' if prim is None else 'Precio primaria no válido'
    elif not sec:
        err = 'Falta precio secundaria' if sec is None else 'Precio secundaria no válido'
    elif old_p is False:
        err = 'Precio antes primaria no válido'
    elif old_s is False:
        err = 'Precio antes secundaria no válido'
    elif active == 'bad':
        err = 'Activo debe ser SI o NO'
    elif featured == 'bad':
        err = 'Destacado debe ser SI o NO'
    else:
        err = ''
    # Un "precio antes" que no es mayor al actual no es una oferta: se ignora.
    old_p = old_p if old_p and prim and old_p > prim else None
    old_s = old_s if old_s and sec and old_s > sec else None
    return {
        'title': title[:TITLE_MAX], 'slug': _make_slug(raw.get('slug'), title) if title else '',
        'plat': plat or plat_raw, 'genre': genre[:GENRE_MAX], 'prim': prim or None, 'sec': sec or None,
        'old_p': old_p, 'old_s': old_s,
        'active': active if 'activo' in present and active != 'bad' else None,
        'featured': featured if 'destacado' in present and featured != 'bad' else None,
        'tagline': _text(raw.get('frase'))[:TAGLINE_MAX] if 'frase' in present else None,
        'notas': str(raw.get('notas') or '').strip() if 'notas' in present else None,
        'cover_url': _text(raw.get('caratula_url')) or (
            _text(raw.get('caratula')) if re.match(r'https?://', _text(raw.get('caratula'))) else ''),
        'cover_tmp': '', 'err': err,
    }


def _web_image(blob):
    """Reduce la carátula a COVER_MAX_WIDTH px de ancho (sin agrandarla, manteniendo
    la proporción) y la convierte a WebP. Si algo falla se guarda la original."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(blob))
        if img.format == 'JPEG':
            img.draft('RGB', (COVER_MAX_WIDTH, COVER_MAX_WIDTH * 4))
        img = ImageOps.exif_transpose(img)
        img = img.convert('RGBA' if img.mode in ('RGBA', 'LA', 'P', 'PA') else 'RGB')
        if img.width > COVER_MAX_WIDTH:
            img = img.resize((COVER_MAX_WIDTH, max(1, round(img.height * COVER_MAX_WIDTH / img.width))),
                             Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, 'WEBP', quality=COVER_QUALITY, method=4)
        return ContentFile(out.getvalue(), name='import.webp')
    except Exception:  # noqa: BLE001
        return ContentFile(blob, name=f'import.{_sniff_image(blob) or "jpg"}')


def _store_tmp_image(blob):
    if not blob or len(blob) > MAX_IMAGE_BYTES:
        return ''
    ext = _sniff_image(blob)
    if not ext:
        return ''
    return default_storage.save(f'{TMP_DIR}/{uuid.uuid4().hex}.{ext}', ContentFile(blob))


def _cleanup_tmp(data):
    for r in (data or {}).get('rows', []):
        if r.get('cover_tmp'):
            try:
                default_storage.delete(r['cover_tmp'])
            except Exception:  # noqa: BLE001
                pass


# ------------------------------------------------------------------ vistas

def products_bulk_view(request):
    ctx = _ctx(request)
    data = request.session.get(SESSION_KEY)
    if data:
        rows = data['rows']
        ok = sum(1 for r in rows if not r['err'])
        cursor = data.get('cursor', 0)
        ctx.update({
            'loaded': True, 'file_name': data['name'], 'n_rows': len(rows), 'ok_count': ok, 'err_count': len(rows) - ok,
            'done': data.get('done'), 'imported': data.get('imported', 0),
            'importing': cursor > 0 and not data.get('done'),
            'progress': sum(1 for r in rows[:cursor] if not r['err']),
            'import_errors': data.get('import_errors', []),
            'n_images': sum(1 for r in rows if r.get('cover_tmp')),
            'n_urls': sum(1 for r in rows if r.get('cover_url') and not r.get('cover_tmp')),
            'rows': [{**r, 'prim_f': money(r['prim'], allow_free=False) if r['prim'] else '—',
                      'sec_f': money(r['sec'], allow_free=False) if r['sec'] else '—',
                      'genre': r['genre'] or '—',
                      'cover': 'Imagen' if r.get('cover_tmp') else ('URL' if r.get('cover_url') else '—')}
                     for r in rows],
        })
    ctx['columns'] = COLUMNS
    ctx['upload_error'] = request.session.pop('bulk_error', None)
    return render(request, 'panel/carga.html', ctx)


def products_bulk_template(request):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Productos'
    ws.append(COLUMNS)
    ws.append(['Hogwarts Legacy', '', 'PS5', 'Aventura', 94900, 149900, None, None, 'SI', 'NO', '', '',
               'https://ejemplo.com/caratula.jpg', None])
    head_fill, head_font = PatternFill('solid', fgColor='6F2DA8'), Font(bold=True, color='FFFFFF')
    for cell in ws[1]:
        cell.fill, cell.font = head_fill, head_font
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    for i in range(1, len(COLUMNS) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 26
    ws.row_dimensions[1].height = 42
    ws.freeze_panes = 'A2'
    info = wb.create_sheet('Instrucciones')
    info.append(['Columna', 'Qué poner'])
    for line in [
        ('Título *', 'Obligatorio.'),
        ('Slug', 'Opcional. Si queda vacío se genera del título. Si ya existe un juego con ese slug, se actualiza.'),
        ('Plataforma *', 'PS4, PS5 o PS4/PS5.'),
        ('Género *', 'Obligatorio (p. ej. Acción/Aventura, Deportes, RPG).'),
        ('Precios (COP) *', 'Números sin puntos ni símbolos (ej. 94900). Los "Precio antes" son opcionales.'),
        ('Activo / Destacado', 'SI o NO. Vacío = Activo SI, Destacado NO.'),
        ('Carátula', 'Pega la imagen en la celda de la fila, o pon su URL en la columna "URL de la carátula".'),
    ]:
        info.append(list(line))
    info.column_dimensions['A'].width = 24
    info.column_dimensions['B'].width = 100
    buf = io.BytesIO()
    wb.save(buf)
    response = HttpResponse(
        buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="plantilla-productos-gangajuegos.xlsx"'
    return response


@require_POST
def products_bulk_upload(request):
    f = request.FILES.get('file')
    if not f or not f.name.lower().endswith(('.csv', '.xlsx')):
        request.session['bulk_error'] = 'Sube un archivo .xlsx (o .csv) con las columnas de la plantilla.'
        return redirect('gsadmin:products_bulk')
    try:
        raw_rows, present = _read_rows(f)
    except Exception as e:  # noqa: BLE001
        request.session['bulk_error'] = f'No se pudo leer el archivo: {e}'
        return redirect('gsadmin:products_bulk')
    missing = [c for c in ('titulo', 'plataforma', 'genero', 'precio_primaria', 'precio_secundaria') if c not in present]
    if missing:
        labels = dict(TEMPLATE_COLUMNS)
        request.session['bulk_error'] = (
            'Al archivo le faltan columnas de la plantilla: ' + ', '.join(labels[c].rstrip(' *') for c in missing) + '.')
        return redirect('gsadmin:products_bulk')
    raw_rows = [r for r in raw_rows
                if any(_text(v) for k, v in r.items() if k != '_image') or r.get('_image')][:MAX_ROWS]
    if not raw_rows:
        request.session['bulk_error'] = 'El archivo no tiene filas con datos.'
        return redirect('gsadmin:products_bulk')
    _cleanup_tmp(request.session.get(SESSION_KEY))
    rows = []
    for raw in raw_rows:
        row = _validate(raw, present)
        if raw.get('_image') and not row['err']:
            row['cover_tmp'] = _store_tmp_image(raw['_image'])
        rows.append(row)
    request.session[SESSION_KEY] = {'name': f.name, 'rows': rows}
    return redirect('gsadmin:products_bulk')


def _fetch_image(url):
    url = url.strip()
    starts = [m.start() for m in re.finditer(r'https?://', url)]
    if len(starts) > 1:
        url = url[starts[-1]:]
    if not url.lower().startswith(('http://', 'https://')):
        return None, 'la URL de la carátula debe empezar con http:// o https://'
    try:
        resp = requests.get(url, timeout=(5, 8), stream=True, headers={'User-Agent': 'Mozilla/5.0 GangaJuegos'})
        resp.raise_for_status()
        chunks, total = [], 0
        for chunk in resp.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                return None, 'la carátula pesa más de 8 MB'
            chunks.append(chunk)
    except requests.RequestException as e:
        return None, f'no se pudo descargar la carátula ({e.__class__.__name__})'
    blob = b''.join(chunks)
    if not _sniff_image(blob):
        return None, 'la URL de la carátula no apunta a una imagen'
    return _web_image(blob), None


def _tmp_image(path):
    try:
        with default_storage.open(path, 'rb') as fh:
            blob = fh.read()
    except Exception:  # noqa: BLE001
        return None, 'no se encontró la imagen pegada (vuelve a subir el archivo)'
    return _web_image(blob), None


def _cover_for(r):
    if r.get('cover_tmp'):
        return _tmp_image(r['cover_tmp'])
    if r.get('cover_url'):
        return _fetch_image(r['cover_url'])
    return None, None


def _save_row(r):
    old_p, old_s = r['old_p'], r['old_s']
    # Si solo viene uno de los "precio antes", el otro se deriva en proporción.
    if old_p and not old_s:
        old_s = round(old_p * r['sec'] / r['prim'] / 100) * 100 or None
        old_s = old_s if old_s and old_s > r['sec'] else None
    elif old_s and not old_p:
        old_p = round(old_s * r['prim'] / r['sec'] / 100) * 100 or None
        old_p = old_p if old_p and old_p > r['prim'] else None
    fields = {
        'title': r['title'], 'platform': r['plat'], 'genre': r['genre'],
        'price_primary': r['prim'], 'price_secondary': r['sec'],
        'old_price_primary': old_p, 'old_price_secondary': old_s,
    }
    for key, field in (('active', 'active'), ('featured', 'featured'), ('tagline', 'tagline'), ('notas', 'notas')):
        if r.get(key) is not None:
            fields[field] = r[key]
    juego, created = Juego.objects.get_or_create(slug=r['slug'], defaults={'active': True, **fields})
    if not created:
        for k, v in fields.items():
            setattr(juego, k, v)
        juego.save()
    return juego


def _attach_cover(juego, content):
    existing = Cover.objects.filter(juego=juego).first()
    if existing and existing.image:
        existing.image.delete(save=False)
    Cover.objects.update_or_create(juego=juego, defaults={'image': content})


@require_POST
def products_bulk_import(request):
    data = request.session.get(SESSION_KEY)
    if not data or data.get('done'):
        return redirect('gsadmin:products_bulk')
    rows = data['rows']
    cursor = data.get('cursor', 0)
    n, errors = data.get('imported', 0), data.get('import_errors', [])
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as pool:
        while cursor < len(rows) and time.monotonic() - started < IMPORT_TIME_BUDGET:
            batch = [r for r in rows[cursor:cursor + IMPORT_BATCH] if not r['err']]
            covers = list(pool.map(_cover_for, batch))
            for r, (content, cover_err) in zip(batch, covers):
                try:
                    juego = _save_row(r)
                except Exception as e:  # noqa: BLE001
                    errors.append(f'{r["title"]}: no se pudo guardar ({e})')
                    continue
                n += 1
                if cover_err:
                    errors.append(f'{r["title"]}: {cover_err}')
                elif content:
                    try:
                        _attach_cover(juego, content)
                    except Exception as e:  # noqa: BLE001
                        errors.append(f'{r["title"]}: no se pudo guardar la carátula ({e})')
                if r.get('cover_tmp'):
                    try:
                        default_storage.delete(r['cover_tmp'])
                    except Exception:  # noqa: BLE001
                        pass
                    r['cover_tmp'] = ''
            cursor += IMPORT_BATCH
    data.update({'cursor': min(cursor, len(rows)), 'imported': n, 'import_errors': errors[:200],
                 'done': cursor >= len(rows)})
    request.session[SESSION_KEY] = data
    return redirect('gsadmin:products_bulk')


@require_POST
def products_bulk_reset(request):
    _cleanup_tmp(request.session.pop(SESSION_KEY, None))
    return redirect('gsadmin:products_bulk')
