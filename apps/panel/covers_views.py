import csv

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.catalog.models import Cover, Juego

from .matching import match_slug


def _initials(title):
    words = [w for w in title.split(' ') if w]
    return ''.join(w[0].upper() for w in words[:2]) or '??'


@require_POST
def covers_upload_ajax(request):
    files = request.FILES.getlist('files')
    games = list(Juego.objects.all().values_list('slug', 'title'))
    ok, orphans = [], []
    for f in files:
        if not f.content_type.startswith('image/'):
            continue
        slug = match_slug(f.name, games)
        if slug:
            juego = Juego.objects.get(slug=slug)
            existing = Cover.objects.filter(juego=juego).first()
            if existing:
                existing.image.delete(save=False)
            cover, _ = Cover.objects.update_or_create(juego=juego, defaults={'image': f})
            ok.append({'slug': slug, 'title': juego.title, 'url': cover.image.url})
        else:
            orphans.append({'name': f.name})
    return JsonResponse({'ok': ok, 'orphans': orphans[:40]})


@require_POST
def covers_assign_one(request, slug):
    juego = get_object_or_404(Juego, slug=slug)
    f = request.FILES.get('file')
    if not f or not f.content_type.startswith('image/'):
        return JsonResponse({'error': 'archivo inválido'}, status=400)
    existing = Cover.objects.filter(juego=juego).first()
    if existing:
        existing.image.delete(save=False)
    cover, _ = Cover.objects.update_or_create(juego=juego, defaults={'image': f})
    return JsonResponse({'slug': slug, 'url': cover.image.url})


@require_POST
def covers_remove(request, slug):
    juego = get_object_or_404(Juego, slug=slug)
    cover = Cover.objects.filter(juego=juego).first()
    if cover:
        cover.image.delete(save=False)
        cover.delete()
    return JsonResponse({'slug': slug})


def covers_export_csv(request):
    covers = set(Cover.objects.values_list('juego__slug', flat=True))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mapeo-caratulas-gamesstation.csv"'
    response.write('﻿')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['slug', 'titulo', 'archivo_caratula', 'cargada'])
    for g in Juego.objects.all().order_by('title'):
        writer.writerow([g.slug, g.title, f'{g.slug}.jpg', 'SI' if g.slug in covers else 'NO'])
    return response
